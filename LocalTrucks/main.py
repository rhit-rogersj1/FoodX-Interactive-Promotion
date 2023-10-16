import csv
import googlemaps
import requests
import folium

# Put my key in to connect to the google API
api_key = 'AIzaSyDdMO9nZW_GnRck1qjuuzded1XoM1rGgGc'
gmaps = googlemaps.Client(key=api_key)


def foodTrucks(location, radius):
    # searches for places that are nearby to the location with that are related to food truck
    localPlaces = gmaps.places_nearby(keyword='food_truck', location=location, radius=radius)

    # url to extract details from a particular food truck
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    # holds all of the food trucks nearby
    foodTrucks = []


    # loops by all of the food truck nearby
    for place in localPlaces.get('results', []):
        # the parametes to be able to get the details providing the place_id of the place and my api key
        params = {
            'place_id': place['place_id'],
            'key': api_key,
            'fields': 'name,formatted_address,website,rating,types,opening_hours,geometry'
        }
        # requests it from the url and return the name,formatted_address,website,rating,types, amdopening_hours
        response = requests.get(url, params=params)
        result = response.json()

        details = result.get('result', {})
        details['formatted_hours'] = hours(details.get('opening_hours', {}))
        foodTrucks.append(details)

    return foodTrucks


def LocalFoodTrucksCsv(result, filename):
    # writes the local food truck into a csv file (called foodTruck.csv)
    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        # the cumumn names are defined
        fieldnames = ['name', 'formatted_address', 'website', 'rating', 'opening_hours', 'types']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)


        # for each item, a row is filled in with the result
        writer.writeheader()
        for details in result:
            writer.writerow({
                'name': details.get('name', 'N/A'),
                'formatted_address': details.get('formatted_address', 'N/A'),
                'website': details.get('website', 'N/A'),
                'rating': details.get('rating', 'N/A'),
                'opening_hours': details.get('formatted_hours', 'N/A'),
                'types': ', '.join(details.get('types', [])),
            })


def hours(opening_hours):
    if 'periods' in opening_hours:
        periods = opening_hours['periods']
        # only allow unique hours
        formatted_hours = set()

        for period in periods:
            open_time = period['open']['time']

            # if the is a close time, sets the close to that otherwise it return n/a
            if 'close' in period:
                close_time = period['close']['time']
                formatted_close_time = f"{close_time[:2]}:{close_time[2:]} {'' if int(close_time[:2]) < 12 else 'PM'}"
            else:
                return 'N/A'

            formatted_open_time = f"{open_time[:2]}:{open_time[2:]} {'' if int(open_time[:2]) < 12 else 'AM'}"
            # adds to set
            formatted_hours.add(f"{formatted_open_time} - {formatted_close_time}")

        return ', '.join(formatted_hours)


def getDirections(origin, destination, mode):
    # returns directions to a destination
    directions_result = gmaps.directions(
        origin,
        destination,
        mode=mode
    )
    # if there are results to the query, fills in information otherwise return n/a n/a n/a
    if directions_result:
        leg = directions_result[0]['legs'][0]
        travel_distance = leg['distance']['text']
        travel_time = leg['duration']['text']
        transportation_type = leg['steps'][0]['travel_mode']
        return travel_distance, travel_time, transportation_type
    else:
        return 'N/A', 'N/A', 'N/A'

def planCSV(details_list, csv_filename, route_info):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csv_file:
        # sets the column names
        fieldnames = ['Time', 'Name', 'Address', 'Rating', 'Opening Hours', 'Distance', 'Travel Time', 'Transportation method']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for details, route in zip(details_list, route_info):
            writer.writerow({
                'Time': route['time'],
                'Name': details.get('name', 'N/A'),
                'Address': details.get('formatted_address', 'N/A'),
                'Rating': details.get('rating', 'N/A'),
                'Opening Hours': details.get('formatted_hours', 'N/A'),
                'Distance': route.get('travel_distance', 'N/A'),
                'Travel Time': route.get('travel_time', 'N/A'),
                'Transportation method': route.get('transportation_type', 'N/A')
            })


def createMap(locations):
    # Check if there are any locations
    if not locations:
        return None

    # sum the total latitude of all location
    total_lat = sum(location['location']['lat'] for location in locations)
    # sum the total longitude of all location
    total_lng = sum(location['location']['lng'] for location in locations)

    # get the center by dividing the amount
    map_center = {'lat': total_lat / len(locations), 'lng': total_lng / len(locations)}

    # Create the map
    my_map = folium.Map(location=[map_center['lat'], map_center['lng']], zoom_start=14)

    for location in locations:
        # get the latitude and longitude
        latitude, longitude = location['location']['lat'], location['location']['lng']

        folium.Marker(
            location=[latitude, longitude],
            popup=f"{location['name']} - Rating: {location['rating']}"
        ).add_to(my_map)

    return my_map



if __name__ == "__main__":
    # latitude and longitude of terre haute
    location = '39.472298,-87.401917'

    # sets the radius of how far to look
    radius = 1000

    # finds the local food trucks
    results = foodTrucks(location, radius=radius)

    # if there are results, it saves it to a csv
    if results:
        LocalFoodTrucksCsv(results, 'foodTruck.csv')

        # sorts food trucks by rating
        sorted_food_trucks = sorted(results, key=lambda x: x.get('rating', 0), reverse=True)

        # sets times to attend food stand and method of getting there
        times = ['09:00 AM', '01:00 PM', '06:00 PM']
        modes = ['driving', 'driving', 'walking']

        # Create a list of locations for the map
        locationsMap = []
        route_info = []

        for i, time in enumerate(times):
            # Check if there are enough food trucks in the sorted list
            if i < len(sorted_food_trucks):
                topFoodTruck = sorted_food_trucks[i]

                destination = topFoodTruck['formatted_address']
                departure_time = f"{time} UTC"
                travel_distance, travel_time, transportation_type = getDirections(location, destination, modes[i])

                topFoodTruck['travel_distance'] = travel_distance
                topFoodTruck['travel_time'] = travel_time
                topFoodTruck['transportation_type'] = transportation_type

                # makes sure location is there
                geometry = topFoodTruck.get('geometry', {})
                loc = geometry.get('location', {})


                # Add the location to the list for the map
                if 'lat' in loc and 'lng' in loc:
                    locationsMap.append({
                        'name': topFoodTruck['name'],
                        'rating': topFoodTruck.get('rating', 'N/A'),
                        'location': loc
                    })

                # Add route information to the list
                route_info.append({
                    'time': time,
                    'travel_distance': travel_distance,
                    'travel_time': travel_time,
                    'transportation_type': transportation_type
                })


        # create a map
        map = createMap(locationsMap)
        map.save('vizualization.html')

        # Save plan as csv
        planCSV(sorted_food_trucks, 'plan.csv', route_info)

# the system finds local food trucks and makes a day plan going to the three highest rated places
# vizualization is in html