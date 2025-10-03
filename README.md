# Aquaponics Web Application

## Setup Instructions for Windows Server 2025 and Waitress

1. Install IIS HTTPHandler (IIS uses this to start the waitress application)
2. Install the latest version of Python
3. Create a folder under c:\intepub

## Creating and Using a Virtual Environment

1. Create a virtual environment:
2. Windows Command Prompt/PowerShell in the base directory

   ```bash
   python -m venv .venv
   ```

3. Activate the virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

6. Install required packages:

   ```bash
   pip install flask waitress requests
   ```

7. Restart the IIS server

   ```bash
   iisreset
   ```

### Setup Waitress with Windows Server IIS

1. Setup folder under inetpub for flask application
3. Configure IIS to use the virtual environment Python interpreter with web.config

---

## Sensors Purchased

### Temperature Sensor

- [Raspberry Pi Temperature Sensor Tutorial](https://pimylifeup.com/raspberry-pi-temperature-sensor/)

### **Gravity: Analog Industrial pH Sensor / Meter Pro Kit V2**

- [DFRobot Wiki Documentation](https://wiki.dfrobot.com/Gravity__Analog_pH_Sensor_Meter_Kit_V2_SKU_SEN0161-V2)
- [GreenPonik pH Python Library](https://github.com/GreenPonik/GreenPonik_PH_Python)

### Non-Contact Water Level Sensor

- [CQRobot Non-Contact Water/Liquid Level Sensor Documentation](http://www.cqrobot.wiki/index.php/Non-Contact_Water/Liquid_Level_Sensor_SKU:_CQRSENYW001)

## Aquaponics Research

- [Controlled Environment Agriculture - Cornell University](https://cea.cals.cornell.edu/)
  - LED light sizing
  - How many moles/lumens per m²

### System Components

- **Oxygenation**
  - More bubblers with fish
  - Bubblers with plants
- **Sump** for circulation of water, pH sensors, health of water without disturbing the fishies
- **Quiet oscillating fan** for plants

### Electrical Conductivity Sensor Options Research

- [MICS6814 Gas Sensor (GitHub)](https://github.com/pimoroni/mics6814-python)
- [Adafruit ENS160 MOX Gas Sensor](https://learn.adafruit.com/adafruit-ens160-mox-gas-sensor)
- [Grove VOC and eCO2 Gas Sensor-SGP30](https://wiki.seeedstudio.com/Grove-VOC_and_eCO2_Gas_Sensor-SGP30/)
- [Scientific research on sensors](https://www.sciencedirect.com/science/article/pii/S2215016123004326)
- [Grove Multichannel Gas Sensor V2](https://wiki.seeedstudio.com/Grove-Multichannel-Gas-Sensor-V2/)
- [Grove Multichannel Gas Sensor](https://wiki.seeedstudio.com/Grove-Multichannel_Gas_Sensor/)
- [Kactoily 7-in-1 Aquarium WiFi Monitor](https://kactoily.com/products/7-in-1-aquarium-wifi-monitor?variant=49385677586725)

---

## Code Summary

- **main_app.py**: The main Flask web application. It provides a web interface for viewing MJPEG video streams from remote cameras, handles configuration, logging, and routes for the web UI. It uses `MediaRelay` and `CachedMediaRelay` to efficiently distribute video streams to multiple clients.

- **frame_cache.py**: Contains the `FrameCache` system, which buffers video frames from unreliable wireless cameras. It stores frames temporarily and serves them with a delay to smooth out connection issues, providing stable video playback.

- **cached_relay.py**: Defines the `CachedMediaRelay` class, which combines the relay and frame caching systems. It provides stable video streaming from unreliable sources by buffering frames and distributing them to clients at a steady rate.

- **waitress_app.py**: Sets up and runs a Waitress WSGI server to serve the Flask web application. It configures logging and ensures the app can be deployed in a production environment. 