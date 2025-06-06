import requests
import json
from typing import Dict, Any, List, Optional
# API reference : https://developer.octopus.energy/graphql/reference/queries#api-queries-devices
try:
    import config  # Ensure config.py is there
except ImportError:
    print("Error: config.py not found. Please create it with your API_KEY and ACCOUNT_NUMBER.")
    exit(1)

OCTOPUS_API_URL = "https://api.octopus.energy/v1/graphql/"

def obtain_session_token(api_key: str) -> str:
    """
    Obtains a session token from Octopus Energy API using the APIKey.
    """
    query = """
    mutation krakenTokenAuthentication($apiKey: String!) {
      obtainKrakenToken(input: {APIKey: $apiKey}) {
        token
      }
    }
    """
    variables = {'apiKey': api_key}
    try:
        response = requests.post(OCTOPUS_API_URL, json={'query': query, 'variables': variables})
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        json_response = response.json()
        if "errors" in json_response and json_response["errors"]:
            error_messages = [err.get('message', 'Unknown error') for err in json_response["errors"]]
            raise Exception(f"GraphQL error while obtaining token: {', '.join(error_messages)}")
        return json_response['data']['obtainKrakenToken']['token']
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f"HTTP error obtaining token: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        raise Exception(f"Request error obtaining token: {req_err}")
    except (KeyError, TypeError) as e:
        raise Exception(f"Error parsing token response: {e} - Response: {response.text}")

def get_account_devices(account_number: str, session_token: str) -> List[Dict[str, Any]]:
    """
    Fetches a list of smart devices registered to an account.

    Args:
        account_number (str): The account number.
        session_token (str): The authenticated session token.

    Returns:
        List[Dict[str, Any]]: A list of devices.
    """
    query_body = """
    query Devices($accountNumber: String!) {
      devices(accountNumber: $accountNumber) {
        id
        name
        deviceType
        provider
        integrationDeviceId
        propertyId
      }
    }
    """
    variables: Dict[str, Any] = {"accountNumber": account_number}
    payload = {"query": query_body, "variables": variables}
    headers = {"Authorization": session_token}

    try:
        response = requests.post(OCTOPUS_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        json_response = response.json()
        if "errors" in json_response and json_response["errors"]:
            error_messages = [err.get('message', 'Unknown error') for err in json_response["errors"]]
            raise Exception(f"GraphQL error fetching account devices: {', '.join(error_messages)}")
        return json_response.get('data', {}).get('devices', [])
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f"HTTP error fetching account devices: {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        raise Exception(f"Request error fetching account devices: {req_err}")
    except (KeyError, TypeError) as e:
        raise Exception(f"Error parsing devices response: {e} - Response: {response.text}")

if __name__ == "__main__":
    try:
        api_key = config.API_KEY
        account_num = config.ACCOUNT_NUMBER

        print("Attempting to obtain session token...")
        session_token = obtain_session_token(api_key)
        print(f"Successfully obtained session token (ends with: ...{session_token[-6:]})")

        print(f"\nFetching devices for account: {account_num}...")
        account_devices = get_account_devices(account_num, session_token)

        if not account_devices:
            print("No devices found for this account.")
        else:
            # print("\n--- Raw JSON for Devices List ---")
            # print(json.dumps(account_devices, indent=2))
            # print("--- End of Raw JSON ---")

            print(f"\nFound {len(account_devices)} device(s):")
            for i, device in enumerate(account_devices):
                print(f"  Device {i+1}:")
                print(f"    Device ID:           {device.get('id')}")
                print(f"    Name:                {device.get('name')}")
                print(f"    Device Type:         {device.get('deviceType')}")
                print(f"    Provider:            {device.get('provider')}")
                print(f"    Integration Dev ID:  {device.get('integrationDeviceId')}")
                print(f"    Property ID:         {device.get('propertyId')}")
                print("-" * 20)

    except AttributeError as e:
        if 'API_KEY' in str(e) or 'ACCOUNT_NUMBER' in str(e):
            print(f"Error: Missing API_KEY or ACCOUNT_NUMBER in config.py. Details: {e}")
        else:
            print(f"An unexpected attribute error occurred: {e}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
