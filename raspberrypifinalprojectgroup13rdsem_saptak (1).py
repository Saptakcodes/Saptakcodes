import os
import glob
from picamera2 import Picamera2
import RPi.GPIO as GPIO
import smtplib
from time import sleep, time
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Email configuration
sender = 'chakisaptak@gmail.com'
password = 'wzln knpe mvxb xzih'
receiver = 'chakisaptak@gmail.com'

DIR = '/home/pi/Pictures'
prefix = 'image'

# GPIO pin configuration for Ultrasonic Sensor and Buzzer
TRIG = 16  # Trigger pin
ECHO = 18  # Echo pin
BUZZER = 22  # Buzzer pin

# Setup GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(BUZZER, GPIO.OUT)

# Initialize PWM on the buzzer pin
#pwm_buzzer = GPIO.PWM(BUZZER, 440)  # Set initial frequency to 440Hz (A4 note)
#pwm_buzzer.start(0)  # Start PWM with 0% duty cycle (off)

# Function to send email with the image attachment
def send_mail(filename):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = 'Visitor'
    body = 'Find the picture in attachments.'
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach the image file
    with open(filename, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(filename)}')
        msg.attach(part)
    
    # Send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Function to capture and save an image
def capture_img():
    print('Capturing image...')
    if not os.path.exists(DIR):
        os.makedirs(DIR)
    files = sorted(glob.glob(os.path.join(DIR, prefix + '[0-9][0-9][0-9].jpg')))
    count = len(files)
    filename = os.path.join(DIR, prefix + '{:03d}.jpg'.format(count))
    
    picam2 = Picamera2()  # Correct usage of Picamera2
    picam2.start_and_capture_file(filename)
    send_mail(filename)

# Function to measure the distance using the ultrasonic sensor
def distance():
    GPIO.output(TRIG, False)
    sleep(0.1)

    GPIO.output(TRIG, True)
    sleep(0.01)
    GPIO.output(TRIG, False)

    pulse_start = time()
    timeout = pulse_start + 0.04  # Set a timeout of 40ms

    while GPIO.input(ECHO) == 0:
        pulse_start = time()
        if pulse_start > timeout:
            print("Timeout: Echo signal not received")
            return None

    pulse_end = time()
    timeout = pulse_end + 0.04  # Set another timeout

    while GPIO.input(ECHO) == 1:
        pulse_end = time()
        if pulse_end > timeout:
            print("Timeout: Echo signal too long")
            return None

    pulse_duration = pulse_end - pulse_start
    measured_distance = pulse_duration * 17150  # Speed of sound (34300 cm/s), divide by 2 for the round trip

    # Validate distance reading
    if measured_distance > 200 or measured_distance <= 2:  # Invalid readings
        print("Failed to measure distance.")
        return None
    return round(measured_distance, 2)

# Function to play a tone
def play_tone(frequency, duration):
    pwm_buzzer.ChangeFrequency(frequency)
    pwm_buzzer.ChangeDutyCycle(100)  # Set duty cycle to 50% (sound on)
    sleep(duration)
    pwm_buzzer.ChangeDutyCycle(0) # Stop sound
    sleep(0.1)

# Main loop to detect objects and trigger actions
last_email_sent = 0
email_delay = 60  # Time in seconds to wait before sending another email
pwm_buzzer = GPIO.PWM(BUZZER, 440)  # Set an initial frequency
pwm_buzzer.start(0)  # Start PWM with 0% duty cycle (off)
try:
    while True:
        dist = distance()
        
        if dist is not None:
            print(f"Distance: {dist} cm")
            if dist < 80:  # Object detected within 80 cm
                print("Object detected. Ringing the buzzer and capturing the image.")
                play_tone(1000, 2)  # Play a 1000Hz tone for 1 second
                
                # Capture and send email if not sent recently
                if time() - last_email_sent > email_delay:
                    capture_img()
                    last_email_sent = time()
                else:
                    print("Email was sent recently. Waiting before sending another.")
                    
                sleep(5)  # Wait for 5 seconds before resetting
            else:
                print("No object detected within range. Waiting...")
        else:
            print("No valid distance measurement. Waiting...")
            
except KeyboardInterrupt:
    print("Exiting...")

finally:
    #pwm_buzzer.stop()  # Stop PWM on exit
    GPIO.cleanup()  # Clean up GPIO on exit
    #GPIO.output(BUZZER,GPIO.LOW)

# Clean up GPIO and stop PWM on exit
GPIO.cleanup()
pwm_buzzer.stop()
