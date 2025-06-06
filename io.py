import requests,json
from datetime import date, datetime,timezone,timedelta
from requests.models import HTTPError
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
try:
    import config  # ensure config..py is in the .gitignore file
except ImportError:
    print("Error: config.py not found. Please create it with your API_KEY, ACCOUNT_NUMBER & DEVICE_ID.")
    exit(1)

url = "https://api.octopus.energy/v1/graphql/"
apikey = config.API_KEY # Your Octopus API Key
accountNumber = config.ACCOUNT_NUMBER # Your Octopus Account Number
deviceId = config.DEVICE_ID # ID to track from e.g. EV Charger (get deviceID from devices API call; https://developer.octopus.energy/graphql/reference/queries#api-queries-devices)   

dateTimeToUse = datetime.now().astimezone()
if dateTimeToUse.hour < 17:
    dateTimeToUse = dateTimeToUse-timedelta(days=1)
ioStart = dateTimeToUse.astimezone().replace(hour=23, minute=30, second=0, microsecond=0)
ioEnd = dateTimeToUse.astimezone().replace(microsecond=0).replace(hour=5, minute=30, second=0, microsecond=0)+timedelta(days = 1)

def refreshToken(apiKey,accountNumber):
    try:
        query = """
        mutation krakenTokenAuthentication($api: String!) {
        obtainKrakenToken(input: {APIKey: $api}) {
            token
        }
        }
        """
        variables = {'api': apikey}
        r = requests.post(url, json={'query': query , 'variables': variables})
    except HTTPError as http_err:
        print(f'HTTP Error {http_err}')
    except Exception as err:
        print(f'Another error occurred: {err}')

    jsonResponse = json.loads(r.text)
    return jsonResponse['data']['obtainKrakenToken']['token']

def get_flex_planned_dispatches(): #Changed from plannedDispatches to flexPlannedDispatches as previous deprecated 2025/05/27 to be removed 2025/08/27. API notice: https://announcements.kraken.tech/announcements/public/166/
    try:
        query = """
            query FlexPlannedDispatches($deviceId: String!) {
                flexPlannedDispatches(deviceId: $deviceId) {
                    start
                    end
                    type
                }
            }
        """
        variables = {'deviceId': deviceId}
        headers = {"Authorization": authToken}
        r = requests.post(url, json={'query': query, 'variables': variables, 'operationName': 'FlexPlannedDispatches'}, headers=headers)
        return json.loads(r.text)['data']
    except HTTPError as http_err:
        print(f'HTTP Error {http_err}')
    except Exception as err:
        print(f'Another error occurred: {err}')

def getTimes():
    object = get_flex_planned_dispatches()
    return object['flexPlannedDispatches']

def returnPartnerSlotStart(startTime):
    for x in times:
        slotStart = datetime.strptime(x['startDt'],'%Y-%m-%d %H:%M:%S%z')
        slotEnd = datetime.strptime(x['endDt'],'%Y-%m-%d %H:%M:%S%z')
        if(startTime == slotEnd):
            return slotEnd

def returnPartnerSlotEnd(endTime):
    for x in times:
        slotStart = datetime.strptime(x['startDt'],'%Y-%m-%d %H:%M:%S%z')
        slotEnd = datetime.strptime(x['endDt'],'%Y-%m-%d %H:%M:%S%z')
        if(endTime == slotStart):
            return slotEnd

#Get Token
authToken = refreshToken(apikey,accountNumber)
times = getTimes()

#Convert to the current timezone
for i,time in enumerate(times):
    slotStart = datetime.strptime(time['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone(ZoneInfo("Europe/London"))
    slotEnd = datetime.strptime(time['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone(ZoneInfo("Europe/London"))
    time['startDt'] = str(slotStart)
    time['endDt'] = str(slotEnd)
    times[i] = time

timeNow = datetime.now(timezone.utc).astimezone()

#Santise Times
#Remove times within 23:30-05:30 slots
newTimes = []
addExtraSlot = True
for i,time in enumerate(times):
    slotStart = datetime.strptime(time['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
    slotEnd = datetime.strptime(time['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
    if(not((ioStart <= slotStart <= ioEnd) and (ioStart <= slotEnd <= ioEnd))):
        if((slotStart <= ioStart) and (ioStart < slotEnd <= ioEnd)):
            time['endDt'] = str(ioStart)
            times[i] = time
        if((ioStart <= slotStart <= ioEnd) and (ioEnd < slotEnd)):
            time['startDt'] = str(ioEnd)
        newTimes.append(time)
    if((slotStart <= ioStart <= slotEnd) and (slotStart <= ioEnd <= slotEnd)):
        #This slot overlaps our IO slot - we need not add it manually at the next step
        addExtraSlot = False
times = newTimes

if(addExtraSlot):
    #Add our IO period
    ioPeriod = json.loads('[{"startDt": "'+str(ioStart)+'","endDt": "'+str(ioEnd)+'"}]')
    times.extend(ioPeriod)
    times.sort(key=lambda x: x['startDt'])

newTimes = []
#Any partner slots a.k.a. slots next to each other
for i,time in enumerate(times):
    while True:
        slotStart = datetime.strptime(time['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
        slotEnd = datetime.strptime(time['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
        if((i+1)<len(times)):
            partnerStart = datetime.strptime(times[i+1]['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
            partnerEnd = datetime.strptime(times[i+1]['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
            if(slotEnd == partnerStart):
                times.pop((i+1))
                time['endDt'] = str(partnerEnd)
                times[i] = time
            else:
                break
        else:
            break

newTimes = []
#Any slots in the past
for i,time in enumerate(times):
    slotStart = datetime.strptime(time['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
    slotEnd = datetime.strptime(time['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
    if(not(slotStart <= timeNow and slotEnd <= timeNow)):
        newTimes.append(time)
times = newTimes

# Check if our array is empty (everything may be in the past)
if(len(times)==0):
    times = json.loads('[{"startDt": "'+str(ioStart)+'","endDt": "'+str(ioEnd)+'"}]')

nextRunStart = datetime.strptime(times[0]['startDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
nextRunEnd = datetime.strptime(times[0]['endDt'],'%Y-%m-%d %H:%M:%S%z').astimezone()
outputJson = {'nextRunStart':nextRunStart , 'nextRunEnd':nextRunEnd, 'timesObj': times, 'updatedAt': dateTimeToUse}
outputJsonString = json.dumps(outputJson, indent=4, default=str)
print(outputJsonString)