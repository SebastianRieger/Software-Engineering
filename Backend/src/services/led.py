from gpiozero import PWMLED
from time import sleep
from typing import Tuple

class LEDService:
    def __init__(self):
        # Initialize RGB LED pins (adjust pin numbers as needed)
        self.red = PWMLED(17)
        self.green = PWMLED(27)
        self.blue = PWMLED(22)
        
    def set_color(self, rgb: Tuple[float, float, float]):
        """Set RGB LED color (values between 0 and 1)"""
        r, g, b = rgb
        self.red.value = r
        self.green.value = g
        self.blue.value = b
        
    def set_brightness(self, brightness: float):
        """Set overall brightness (0-1)"""
        current_r = self.red.value
        current_g = self.green.value
        current_b = self.blue.value
        
        self.red.value = current_r * brightness
        self.green.value = current_g * brightness
        self.blue.value = current_b * brightness
        
    def fade_to_color(self, rgb: Tuple[float, float, float], duration: float = 1.0):
        """Smoothly transition to a new color"""
        target_r, target_g, target_b = rgb
        start_r = self.red.value
        start_g = self.green.value
        start_b = self.blue.value
        
        steps = 50
        sleep_time = duration / steps
        
        for i in range(steps + 1):
            progress = i / steps
            
            self.red.value = start_r + (target_r - start_r) * progress
            self.green.value = start_g + (target_g - start_g) * progress
            self.blue.value = start_b + (target_b - start_b) * progress
            
            sleep(sleep_time)
            
    def turn_off(self):
        """Turn off all LEDs"""
        self.red.value = 0
        self.green.value = 0
        self.blue.value = 0