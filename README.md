# Intelligent Octopus Scheduler
Quick Python script to query using GraphQL your slots for [Intelligent Octopus](https://octopus.energy/intelligent-octopus/). I use this with Home Assistant to run my automations.

I haven't explained the logic well in the script but I wanted to prevent my automations from triggering on/off through the day. The script checks if there is a slot adjacent to it and if the slot is in the off-peak period. There are most likely some edge usecases where the script won't output the correct times - in my limited testing (and simluating different use cases) it has been working.

**Note:** The script now uses `flexPlannedDispatches` due to breaking changes in the Octopus API instead of `plannedDispatches` [Announcment](https://announcements.kraken.tech/announcements/public/166/). This changes requires you to use the deviceID not just the account number to query.

## config.py
Create a `config.py` file with your credentials:

```python
# config.py
API_KEY = "your-octopus-developer-api-key"
ACCOUNT_NUMBER = "your-octopus-account-number"
DEVICE_ID = "your-device-id"  # See below for how to get this
```

## get_device_id.py
This script should fetch a list of your DEVICE_ID's but it needs the config.py to at least contain the API KEY and ACCOUNT NUMBER to do this by using the [devices API call](https://developer.octopus.energy/graphql/reference/queries#api-queries-devices). It has only been tested with 1x Zappi charger. It is unclear what it will return if you have multiple devices, but its assumed you can work out what one to track (e.g. EV charger). 

```bash
python3 get_devices_id.py
```
Note down and then add the device ID to the config.py file yourself.

## io.py
Ensure all three variables are in the config.py before executing the script:
- [Octopus Developer API Key](https://octopus.energy/dashboard/developer/)
- Octopus Account Number (found on your account section)
- Device ID (see above)

### Check run in terminal
```bash
python3 io.py
```

## Home Assistant
Add the code below to your config to call the python script. 

```yaml
sensor:
  - platform: command_line
    name: Intelligent Octopus Times
    json_attributes:
      - nextRunStart
      - nextRunEnd
      - timesObj
    command: "python3 /config/io.py"
    scan_interval: 3600
    value_template: "{{ value_json.updatedAt }}"

template:
  - binary_sensor:
    - name: "Octopus Intelligent Slot"
      state: '{{ as_timestamp(states("sensor.intelligent_octopus_start")) <= as_timestamp(now()) <= as_timestamp(states("sensor.intelligent_octopus_end")) }}'
  - sensor:
    - name: 'Intelligent Octopus Start'
      state: '{{ state_attr("sensor.intelligent_octopus_times","nextRunStart") }}'
    - name: 'Intelligent Octopus End'
      state: '{{ state_attr("sensor.intelligent_octopus_times","nextRunEnd") }}'
```

In your automations, you can use `binary_sensor.octopus_intelligent_slot`.

## Changelog

### (2024-06-06)
- Switched `io.py` to using `flexPlannedDispatches` due to Octopus API changes (see [announcement](https://announcements.kraken.tech/announcements/public/166/)).
- Added `config.py` for DEVICE_ID, ACCOUNT_NUMBER and API_KEY.
- Added `get_device_id.py` script to help fetch your device ID.