import requests
from datetime import datetime
import time
from twilio.rest import Client
from dotenv import load_dotenv
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


load_dotenv()
#info for text message service twilio
account_sid = os.getenv('ACCOUNT_SID')
auth_token = os.getenv('AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_NUMBER')
my_number = os.getenv('MY_NUMBER')
client = Client(account_sid, auth_token)

#info for distance
geocoder=Nominatim(user_agent='Appointment_API')

# vax_site_coords should be in a tuple with signed (latitude, longitude)
def calculate_site_distance_from_user(vax_site_coords):
    home = (44.9956 , -93.2581)
    distance = geodesic(home,vax_site_coords).miles
    return distance

# json data is swapped, so run it through this before using calculate_site_distance_from_user function
def coordinate_swap(backwards_coordinates):
    forwards_coordinates=(backwards_coordinates[1], backwards_coordinates [0])
    return forwards_coordinates

    

#download and parse data from API
def pull_API():
    # current_time = datetime.now().isoformat()[10:19]
    # print(f'Pulling API {current_time}')
    req=requests.get('https://www.vaccinespotter.org/api/v0/states/MN.json')
    json_data = req.json()['features']
    cleaned_data = []
    acceptable_distance_from_user = 25
    for data in json_data:
        site_properties = data['properties']
        site_geometry = data['geometry']
        if site_properties['postal_code'] is None:
            continue
        cleaned_city = site_properties['city'].lower()
        vax_site_distance = calculate_site_distance_from_user(coordinate_swap(site_geometry['coordinates']))
        if vax_site_distance:
            if vax_site_distance <= acceptable_distance_from_user:
                cleaned_data.append(
                    {
                        'provider_name': site_properties['provider_brand_name'].lower(),
                        'site_name': site_properties['name'].lower(),
                        'address': f'{site_properties["address"].lower()}, '
                                   f'{cleaned_city}, MN,'
                                   f' {site_properties["postal_code"]}',
                        'site_distance': vax_site_distance,
                        'provider_location_id': site_properties['provider_location_id'],
                        'url': site_properties['url'],
                        'appointments': site_properties['appointments']
                    }
                )
    #now look for which sites have availabilty
    available_appointments = {} 
    for site in cleaned_data:
        if site['appointments']:
            if site['provider_name'] not in available_appointments:
                available_appointments[site['provider_name']] = {'available_apts': len(site['appointments']), 'website': site['url']}
            else:
                available_appointments[site['provider_name']]['available_apts'] += len(site['appointments'])
    return available_appointments
#just going to have the loop end when it finds something. Not sure how to keep it from spamming my phone if the API goes wild overnight or something
x = 0
old_available_appointments = pull_API()
while True:
    dt = datetime.now()
    curr_seconds = dt.second
    if (curr_seconds % 60 == 0):
        available_appointments = pull_API()
        if available_appointments and (not old_available_appointments == available_appointments):
            print(old_available_appointments)
            print(available_appointments)
            message = client.messages.create(
                to=my_number, 
                from_=twilio_number,
                body= "Get that appointment! https://www.vaccinespotter.org/MN/?zip=55413&radius=25")
            time.sleep(600)
            old_available_appointments = available_appointments
        time.sleep(1)