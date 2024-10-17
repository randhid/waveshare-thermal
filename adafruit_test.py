import board
import busio
import adafruit_mlx90640
import time





def read_temperature():
    try:
        # Read the thermal image
        mlx.getFrame(frame)

        # Print temperatures for each pixel
        for i in range(0, 192):  # 192 pixels in a 32x24 array
            print(f"Pixel {i}: {frame[i]:.2f} °C")

    except Exception as e:
        print(f"Error reading temperature: {e}")

def main():
    while True:
        read_temperature()
        time.sleep(1)  # Adjust the delay as needed

if __name__ == "__main__":
    main()
