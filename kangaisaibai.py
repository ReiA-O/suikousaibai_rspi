# -*- coding:utf-8 -*-
#!/usr/bin/python3

from sched import scheduler
import requests
import smbus
import time
import datetime
import RPi.GPIO as GPIO
from gpiozero import MCP3002
from gpiozero.pins.pigpio import PiGPIOFactory
import cgsensor
import schedule
from csv import writer


#初期設定#

#LINE用トークンとアドレスと準備する物＜！！！トークンの扱いに注意！！！＞
line_token = 'LINE NOTIFYのトークン'
line_api = 'https://notify-api.line.me/api/notify'
message = ["ステータス"]
Light_ON_message_send_check = False
Light_OFF_message_send_check = False
pump_message_send_check = False

# LINE用メイン関数
def LINE_send():
    send_line_message(message)

def send_line_message(notification_message):
    headers = {'Authorization': f'Bearer {line_token}'}
    data = {'message': f' {notification_message}'}
    requests.post(line_api, headers = headers, data = data)

#GPIOセッティング
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

#使うGPIO決める
LED_GPIO = 18
pump_GPIO = 24

GPIO.setup(LED_GPIO , GPIO.OUT)
GPIO.setup(pump_GPIO , GPIO.OUT)

#センサー初期化
DRY_THRESH = 0.60
WETorDRY = "DRY"
hyouji_WETorDRY = "DRY"
adc_ch0 = MCP3002(channel=0, max_voltage=3.3, pin_factory=PiGPIOFactory())
sensorvalue = adc_ch0.value

bme280 = cgsensor.BME280(i2c_addr=0x76)

#ポンプの状態
pump_ON_OFF = "OFF"

#ライトの状態
TurnON_or_OFF = "OFF"
LIGHT_check = "start"

#いじるな(キャラ表示機)
I2C_ADDR = 0x27
LCD_WIDTH = 16
LCD_CHR = 1
LCD_CMD = 0
LCD_LINE_1 = 0x80
LCD_LINE_2 = 0xC0
LCD_BACKLIGHT = 0x08

#表示時間の設定
bus = smbus.SMBus(1)

# util for LCD
#いじるな(キャラ表示機)
def init_display():
    send_byte_to_data_pin(0x33,LCD_CMD)
    send_byte_to_data_pin(0x32,LCD_CMD)
    send_byte_to_data_pin(0x06,LCD_CMD)
    send_byte_to_data_pin(0x0C,LCD_CMD)
    send_byte_to_data_pin(0x28,LCD_CMD)
    send_byte_to_data_pin(0x01,LCD_CMD)
    time.sleep(0.0005)

#いじるな(キャラ表示機)
def send_byte_to_data_pin(bits,mode):
    upper_bits = mode| (bits & 0xF0) | LCD_BACKLIGHT
    lower_bits = mode | ((bits<<4) & 0xF0)| LCD_BACKLIGHT
    bus.write_byte(I2C_ADDR, upper_bits)
    enable_toggle_button(upper_bits)
    bus.write_byte(I2C_ADDR, lower_bits)
    enable_toggle_button(lower_bits)

#いじるな(キャラ表示機)
def enable_toggle_button(bits):
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits | 0b00000100))
    time.sleep(0.0005)
    bus.write_byte(I2C_ADDR, (bits & ~0b00000100))
    time.sleep(0.0005)

#いじるな(キャラ表示機)
def send_string_to_display(message,line):
    message = message.ljust(LCD_WIDTH, " ")
    send_byte_to_data_pin(line, LCD_CMD)
    for i in range(LCD_WIDTH):
        send_byte_to_data_pin(ord(message[i]),LCD_CHR)

#実務#

# schedule manage
current_time = datetime.datetime.now()
working_day = current_time.day

kyou = datetime.datetime.now()
kyou = kyou.strftime('%Y,%m,%d,%H,%M')
kyou = kyou.split(',')

#日付格納
toshi = kyou[0]
tuki = kyou[1]
hiduke = kyou[2]
jikan = kyou[3]
fun = kyou[4]

honjitu = str(toshi) + "/" +  str(tuki)  + "/" + str(hiduke) + " " + str(jikan) + ":" + str(fun)
honjitu_h = str(toshi) + str(tuki) + str(hiduke)

def CSVjob():
    csv_data = ['{}'.format(honjitu) , '{}'.format(bme280.pressure) , '{}'.format(bme280.temperature) , '{}'.format(bme280.humidity) , '{}'.format(sensorvalue)]
    print("kakikomi")
    with open(honjitu_h + ".csv" , "a" , newline = "") as f_object:
        writer_object = writer(f_object)
        writer_object.writerow(csv_data)
        f_object.close()

schedule.every(15).minutes.do(CSVjob)

try:
    # LCD start up
    init_display()
    # Starting message
    send_string_to_display("hajimaruyo-", LCD_LINE_1) #ここで表示内容をいじる
    send_string_to_display("waai" , LCD_LINE_2) #ここで表示内容をいじる
    
    while True:
        # 日付が変わった時の処理
        current_time = datetime.datetime.now()
        if working_day != current_time.day:
            # day was changed, day status update
            working_day = current_time.day
            WETorDRY = "DRY"
            pump_ON_OFF = "OFF"
            Light_ON_message_send_check = False
            Light_OFF_message_send_check = False
            pump_message_send_check = False
        
        
        kyou = datetime.datetime.now()
        kyou = kyou.strftime('%Y,%m,%d,%H,%M')
        kyou = kyou.split(',')

        #日付格納
        toshi = kyou[0]
        tuki = kyou[1]
        hiduke = kyou[2]
        jikan = kyou[3]
        fun = kyou[4]
        
        honjitu = str(toshi) + "/" +  str(tuki)  + "/" + str(hiduke) + " " + str(jikan) + ":" + str(fun)
        honjitu_h = str(toshi) + str(tuki) + str(hiduke)


        #LED制御用時間設定(6:00-18:00)
        Light_ON_time = datetime.datetime(current_time.year,current_time.month,current_time.day,6,00,00)
        Light_OFF_time = datetime.datetime(current_time.year,current_time.month,current_time.day,18,00,00)

        #ポンプ制御用時間(7:00-7:01)
        pump_ON_time = datetime.datetime(current_time.year,current_time.month,current_time.day,7,00,00)
        pump_OFF_time = datetime.datetime(current_time.year,current_time.month,current_time.day,7,1,00)

        #キャラクタ表示機用時間取得設定(16桁以内)
        time_hyouji = str(current_time.year) + "/" + str(current_time.month) + "/" + str(current_time.day) + " " + str(current_time.hour) + ":" + str(current_time.minute)
        
        print(time_hyouji + "\n") #テスト用プリント

        bme280.forced()  # Forcedモードで測定を行い, 結果をtemperature, pressure, humidityに入れる
        print('気圧 {}hPa'.format(bme280.pressure))  # 気圧を取得して表示
        print('気温 {}°C'.format(bme280.temperature))  # 気温を取得して表示
        print('湿度 {}%'.format(bme280.humidity))  # 湿度を取得して表示
        print("\n")

        send_string_to_display(time_hyouji, LCD_LINE_1) #ここで表示内容をいじる
        
        #LED電灯の時間オンオフ
        if (Light_ON_time < current_time) and (current_time < Light_OFF_time): #(6:00-18:00でオン)
            if TurnON_or_OFF == "OFF": #消えてたら
                GPIO.output(LED_GPIO , True) #つける
                TurnON_or_OFF = "ON" #光ついてるよって言う
                LIGHT_check = "ON"
        else: #時間外
            GPIO.output(LED_GPIO , False) #光を消す
            TurnON_or_OFF = "OFF" #光消えてるよっていう
            LIGHT_check = "OFF"

        print("LIGHT=" + LIGHT_check) #テスト用プリント

        # _/_/_/_/_/_/_/
        # ポンプのオンオフ
        # _/_/_/_/_/_/_/
        # 1. センサーから値を取ってきてて
        # 2. 値に連動してポンプ ON/OFF の処理

        #センサー値取得
        sensorvalue = adc_ch0.value

        if sensorvalue < DRY_THRESH:
            send_string_to_display('T={} '.format(bme280.temperature) + f"S={sensorvalue:.2f}" + " W", LCD_LINE_2)
        else:
            send_string_to_display('T={} '.format(bme280.temperature) + f"S{sensorvalue:.2f}" + " D", LCD_LINE_2)

        if sensorvalue < DRY_THRESH:
            WETorDRY = "WET"
        else:
            WETorDRY = "DRY"

        #テストの際はこいつを有効化
        # WETorDRY = "DRY"
        # WETorDRY = "WET"
        if (pump_ON_time < current_time) and (current_time < pump_OFF_time): #(7:00-7:01の間の時間で)
            print(f"Sensor :{sensorvalue:.2f}")
            if  (sensorvalue > DRY_THRESH) and (WETorDRY == "DRY"): #(土が乾いていたら)
                print("Pump:ON")
                GPIO.output(pump_GPIO , True) #(ポンプをオンにする)
                pump_ON_OFF = "ON"
                time.sleep(10) #10秒流す
                GPIO.output(pump_GPIO , False) #水を止める
                # pump_ON_OFF = "OFF"
                # WETorDRY = "WET" #湿っている状態
                print("status:" + WETorDRY)
            else:
                GPIO.output(pump_GPIO , False)
                print("Pump:OFF")
                # WETorDRY = "WET"

        print("ステータス確認:" + WETorDRY)
        print(f"センサー値： {sensorvalue:.2f}") #テスト用プリント

        print("____________________")

        # #LINE用#

        LINE_Light_ON_check_time_1 = datetime.datetime(current_time.year,current_time.month,current_time.day,6,0,00)
        LINE_Light_ON_check_time_2 = datetime.datetime(current_time.year,current_time.month,current_time.day,6,1,00)
        LINE_Light_OFF_check_time_1 = datetime.datetime(current_time.year,current_time.month,current_time.day,18,0,00)
        LINE_Light_OFF_check_time_2 = datetime.datetime(current_time.year,current_time.month,current_time.day,18,1,00)
        LINE_pump_check_time_1 = datetime.datetime(current_time.year,current_time.month,current_time.day,7,0,00)
        LINE_pump_check_time_2 = datetime.datetime(current_time.year,current_time.month,current_time.day,7,1,00)

        #ライトがオンになったかどうかの通知
        if (LINE_Light_ON_check_time_1 < current_time) and (current_time < LINE_Light_ON_check_time_2) and (Light_ON_message_send_check == False):
            if TurnON_or_OFF == "ON":
                message = ["LIGHT_Status :" + LIGHT_check + '気圧 {}hPa'.format(bme280.pressure) + '気温 {}°C'.format(bme280.temperature) + '湿度 {}%'.format(bme280.humidity)]
                LINE_send()
                Light_ON_message_send_check = True

        #ライトがオフになったかどうかの通知
        if (LINE_Light_OFF_check_time_1 < current_time) and (current_time < LINE_Light_OFF_check_time_2) and (Light_OFF_message_send_check == False):
            if TurnON_or_OFF == "OFF":
                message = ["\nLIGHT_Status :" + LIGHT_check + '\n気圧 {}hPa'.format(bme280.pressure) + '\n気温 {}°C'.format(bme280.temperature) + '\n湿度 {}%'.format(bme280.humidity)]
                LINE_send()
                Light_OFF_message_send_check = True

        #ポンプが作動したかどうかの通知
        if (LINE_pump_check_time_1 < current_time) and (current_time < LINE_pump_check_time_2):
            if pump_ON_OFF == "ON":
                message = ["\npump:ON status : " + WETorDRY + f"\nsensor : {sensorvalue:.2f}"]
                LINE_send()
                pump_ON_OFF = "OFF"
            else:
                if (pump_ON_OFF == "OFF") and (pump_message_send_check == False):
                    message = ["\npump:OFF status : " + WETorDRY + f"\nsensor : {sensorvalue:.2f}" + '\n気圧 {}hPa'.format(bme280.pressure) + '\n気温 {}°C'.format(bme280.temperature) + '\n湿度 {}%'.format(bme280.humidity)]
                    LINE_send()
                    pump_message_send_check = True

        schedule.run_pending()

        time.sleep(1)

except Exception as err_txt:
    print("----- Error! -----")
    print(str(err_txt))
    pass
finally:
    LCD_BACKLIGHT = 0x00
    send_byte_to_data_pin(0x01, LCD_CMD)
    #クリーンナップ#
    GPIO.cleanup()
