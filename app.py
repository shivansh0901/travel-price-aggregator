from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
from config import SERPAPI_KEY, GEMINI_API_KEY
import time
from datetime import datetime



app = Flask(__name__)
CORS(app)

# Configurations
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

# Currency conversion rates (as of March 24, 2025)
CURRENCY_RATES = {
    'USD': 1.0,
    'EUR': 0.92,
    'GBP': 0.78,
    'JPY': 150.25,
    'INR': 83.45
}

def convert_currency(amount, from_currency='USD', to_currency='USD'):
    """Convert amount from one currency to another using stored rates"""
    if from_currency == to_currency:
        return amount
    
    # Convert from source currency to USD (our base currency)
    amount_in_usd = amount / CURRENCY_RATES.get(from_currency, 1.0)
    
    # Convert from USD to target currency
    return amount_in_usd * CURRENCY_RATES.get(to_currency, 1.0)

# Google OAuth (Dummy Implementation)
@app.route('/login')
def login():
    return redirect("https://accounts.google.com/o/oauth2/auth") # Dummy redirect

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Mapping Airlines to Their Official Booking Websites
AIRLINE_WEBSITES = {
    # Indian Airlines
    "Air India": "https://www.airindia.in/",
    "IndiGo": "https://www.goindigo.in/",
    "SpiceJet": "https://www.spicejet.com/",
    "Vistara": "https://www.airvistara.com/",
    "Go First": "https://www.flygofirst.com/",
    "Akasa Air": "https://www.akasaair.com/",
    "Alliance Air": "http://www.allianceair.in/",
    "Air India Express": "https://www.airindiaexpress.in/",
    
    # North American Airlines
    "United Airlines": "https://www.united.com/",
    "American Airlines": "https://www.aa.com/",
    "Delta Airlines": "https://www.delta.com/",
    "Southwest Airlines": "https://www.southwest.com/",
    "JetBlue": "https://www.jetblue.com/",
    "Alaska Airlines": "https://www.alaskaair.com/",
    "Air Canada": "https://www.aircanada.com/",
    "WestJet": "https://www.westjet.com/",

    # European Airlines
    "British Airways": "https://www.britishairways.com/",
    "Lufthansa": "https://www.lufthansa.com/",
    "Air France": "https://wwws.airfrance.us/",
    "KLM": "https://www.klm.com/",
    "Swiss International Air Lines": "https://www.swiss.com/",
    "Austrian Airlines": "https://www.austrian.com/",
    "Turkish Airlines": "https://www.turkishairlines.com/",
    "Finnair": "https://www.finnair.com/",
    "Iberia": "https://www.iberia.com/",
    "SAS (Scandinavian Airlines)": "https://www.flysas.com/",
    "LOT Polish Airlines": "https://www.lot.com/",
    "Aer Lingus": "https://www.aerlingus.com/",
    "TAP Air Portugal": "https://www.flytap.com/",
    "Virgin Atlantic": "https://www.virginatlantic.com/",
    
    # Middle Eastern Airlines
    "Emirates": "https://www.emirates.com/",
    "Etihad Airways": "https://www.etihad.com/",
    "Qatar Airways": "https://www.qatarairways.com/",
    "Saudia": "https://www.saudia.com/",
    "Oman Air": "https://www.omanair.com/",
    "Kuwait Airways": "https://www.kuwaitairways.com/",
    "Gulf Air": "https://www.gulfair.com/",
    
    # Asian Airlines
    "Singapore Airlines": "https://www.singaporeair.com/",
    "Cathay Pacific": "https://www.cathaypacific.com/",
    "Malaysia Airlines": "https://www.malaysiaairlines.com/",
    "ANA (All Nippon Airways)": "https://www.ana.co.jp/",
    "Japan Airlines": "https://www.jal.co.jp/",
    "Korean Air": "https://www.koreanair.com/",
    "Asiana Airlines": "https://www.flyasiana.com/",
    "Thai Airways": "https://www.thaiairways.com/",
    "Garuda Indonesia": "https://www.garuda-indonesia.com/",
    "China Southern Airlines": "https://www.csair.com/",
    "China Eastern Airlines": "https://www.ceair.com/",
    "Air China": "https://www.airchina.com/",
    "Vietnam Airlines": "https://www.vietnamairlines.com/",
    "Philippine Airlines": "https://www.philippineairlines.com/",
    "EVA Air": "https://www.evaair.com/",
    "Bamboo Airways": "https://www.bambooairways.com/",
    
    # African Airlines
    "Ethiopian Airlines": "https://www.ethiopianairlines.com/",
    "South African Airways": "https://www.flysaa.com/",
    "Kenya Airways": "https://www.kenya-airways.com/",
    "EgyptAir": "https://www.egyptair.com/",
    "Royal Air Maroc": "https://www.royalairmaroc.com/",

    # Oceanian Airlines
    "Qantas": "https://www.qantas.com/",
    "Virgin Australia": "https://www.virginaustralia.com/",
    "Air New Zealand": "https://www.airnewzealand.com/",
    "Fiji Airways": "https://www.fijiairways.com/",
}


@app.route('/search_flights', methods=['GET'])
def search_flights():
    origin = request.args.get('origin').upper()
    destination = request.args.get('destination').upper()
    outbound_date = request.args.get('date')
    return_date = request.args.get('return_date', '') # Optional return date
    currency = request.args.get('currency', 'USD')
    flight_class = request.args.get('class', 'Economy')
    passengers = request.args.get('passengers', '1')
    
    # Determine if one-way or round trip
    flight_type = 1 if return_date else 2  # 1 for round trip, 2 for one way
    
    # We'll use USD for the API call and convert later
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "currency": "USD",  # Always request in USD
        "type": flight_type,
        "api_key": SERPAPI_KEY
    }
    
    if return_date:
        params["return_date"] = return_date
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        flight_data = response.json()
        
        # Process flight data
        best_flights = flight_data.get("best_flights", [])
        other_flights = flight_data.get("other_flights", [])
        
        # Combine flights and add booking links
        all_flights = []
        
        for flight_list in [best_flights, other_flights]:
            for flight in flight_list:
                # Get airline info
                airline = flight["flights"][0]["airline"] if "flights" in flight and len(flight["flights"]) > 0 else "Unknown"
                airline_logo = flight["flights"][0].get("airline_logo", "") if "flights" in flight and len(flight["flights"]) > 0 else ""
                
                # Get flight details
                departure_airport = flight["flights"][0]["departure_airport"]["id"] if "flights" in flight and len(flight["flights"]) > 0 else ""
                departure_airport_name = flight["flights"][0]["departure_airport"].get("name", "") if "flights" in flight and len(flight["flights"]) > 0 else ""
                arrival_airport = flight["flights"][-1]["arrival_airport"]["id"] if "flights" in flight and len(flight["flights"]) > 0 else ""
                arrival_airport_name = flight["flights"][-1]["arrival_airport"].get("name", "") if "flights" in flight and len(flight["flights"]) > 0 else ""
                departure_time = flight["flights"][0]["departure_airport"]["time"] if "flights" in flight and len(flight["flights"]) > 0 else ""
                arrival_time = flight["flights"][-1]["arrival_airport"]["time"] if "flights" in flight and len(flight["flights"]) > 0 else ""
                duration = flight.get("total_duration", "")
                
                # Get price and convert currency if needed
                try:
                    price_str = str(flight.get("price", "0"))
                    price_usd = float(price_str.replace("$", "").replace(",", ""))
                    if price_usd == 0.0:
                        continue  # Skip flights with zero price
                except ValueError:
                    continue  # Skip flights with invalid price format
                
                price_converted = convert_currency(price_usd, 'USD', currency)
                
                # Format price with currency symbol
                currency_symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'INR': '₹'}
                symbol = currency_symbols.get(currency, currency + ' ')
                price = f"{symbol}{price_converted:.2f}"
                
                # Get airplane info
                airplane = flight["flights"][0].get("airplane", "") if "flights" in flight and len(flight["flights"]) > 0 else ""
                
                # Get travel class
                travel_class = flight["flights"][0].get("travel_class", flight_class) if "flights" in flight and len(flight["flights"]) > 0 else flight_class
                
                # Get the departure token for direct booking
                departure_token = flight.get("departure_token", "")
                
                # Create booking link using departure token if available
                if departure_token:
                    booking_link = f"https://www.google.com/travel/flights/booking?flt={departure_token}"
                else:
                    # Fallback to airline website if token is not available
                    booking_link = AIRLINE_WEBSITES.get(airline, "https://www.google.com/travel/flights")
                
                # Get stops information
                stops = len(flight.get("flights", [])) - 1
                layovers = flight.get("layovers", [])
                
                flight_info = {
                    "airline": airline,
                    "airline_logo": airline_logo,
                    "departure_airport": departure_airport,
                    "departure_airport_name": departure_airport_name,
                    "arrival_airport": arrival_airport,
                    "arrival_airport_name": arrival_airport_name,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "duration": duration,
                    "price": price,
                    "airplane": airplane,
                    "travel_class": travel_class,
                    "booking_link": booking_link,
                    "stops": stops,
                    "layovers": layovers
                }
                
                all_flights.append(flight_info)
        
        return render_template('flight-results.html', flights=all_flights, origin=origin, destination=destination, outbound_date=outbound_date, return_date=return_date, selected_currency=currency, flight_data=flight_data)
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching flight data: {str(e)}"
        return render_template('flight-results.html', error=error_message)



# Hotel Search (Amadeus API)
@app.route('/search_hotels', methods=['GET'])
def search_hotels():
    city = request.args.get('city')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    rooms = request.args.get('rooms', '1')
    guests = request.args.get('guests', '1')
    currency = request.args.get('currency', 'USD')
    
    # We'll use USD for the API call and convert later
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_hotels",
        "q": f"hotels in {city}",
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": guests,
        "currency": "USD",  # Always request in USD
        "api_key": SERPAPI_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        hotel_data = response.json()
        
        # Process hotel data
        all_hotels = []
        
        for hotel in hotel_data.get("properties", []):
            # Get hotel info
            hotel_name = hotel.get("name", "Unknown Hotel")
            hotel_address = hotel.get("address", "")
            hotel_description = hotel.get("description", "")
            
            # Get hotel class/rating
            hotel_class = hotel.get("hotel_class", "")
            extracted_hotel_class = hotel.get("extracted_hotel_class", 0)
            
            # Get overall rating
            overall_rating = hotel.get("overall_rating", 0)
            reviews_count = hotel.get("reviews", 0)
            
            # Get check-in/check-out times
            check_in_time = hotel.get("check_in_time", "")
            check_out_time = hotel.get("check_out_time", "")
            
            # Get hotel deal if available
            deal = hotel.get("deal", "")
            deal_description = hotel.get("deal_description", "")
            
            # Get hotel amenities
            amenities = hotel.get("amenities", [])
            
            # Get hotel image - try multiple possible locations
            hotel_image = ""
            if "images" in hotel and len(hotel.get("images", [])) > 0:
                hotel_image = hotel.get("images", [])[0].get("thumbnail", "")
            elif "thumbnail" in hotel:
                hotel_image = hotel.get("thumbnail", "")
            
            # Get price and convert currency if needed
            price_usd = 0.0
            try:
                # Try different possible price fields
                if "price" in hotel:
                    price_str = str(hotel.get("price", "0"))
                elif "total_rate" in hotel and "lowest" in hotel.get("total_rate", {}):
                    price_str = str(hotel.get("total_rate", {}).get("lowest", "0"))
                elif "rate_per_night" in hotel and "lowest" in hotel.get("rate_per_night", {}):
                    price_str = str(hotel.get("rate_per_night", {}).get("lowest", "0"))
                else:
                    price_str = "0"
                
                price_usd = float(price_str.replace("$", "").replace(",", ""))
                if price_usd == 0.0:
                    continue  # Skip hotels with zero price
            except ValueError:
                continue  # Skip hotels with invalid price format
            
            price_converted = convert_currency(price_usd, 'USD', currency)
            
            # Format price with currency symbol
            currency_symbols = {'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥', 'INR': '₹'}
            symbol = currency_symbols.get(currency, currency + ' ')
            price = f"{symbol}{price_converted:.2f}"
            
            # Get booking link
            booking_link = hotel.get("link", "https://www.booking.com")
            
            # Get nearby places
            nearby_places = hotel.get("nearby_places", [])
            
            hotel_info = {
                "name": hotel_name,
                "address": hotel_address,
                "description": hotel_description,
                "rating": overall_rating,
                "reviews_count": reviews_count,
                "hotel_class": hotel_class,
                "extracted_hotel_class": extracted_hotel_class,
                "image": hotel_image,
                "price": price,
                "price_value": price_converted,  # For sorting
                "booking_link": booking_link,
                "check_in_time": check_in_time,
                "check_out_time": check_out_time,
                "deal": deal,
                "deal_description": deal_description,
                "amenities": amenities[:5] if amenities else [],  # Limit to 5 amenities for display
                "nearby_places": nearby_places[:3] if nearby_places else []  # Limit to 3 nearby places
            }
            
            all_hotels.append(hotel_info)
        
        return render_template('hotel-results.html', hotels=all_hotels, city=city, check_in=check_in, check_out=check_out, selected_currency=currency, total_nights=(datetime.strptime(check_out, '%Y-%m-%d') - datetime.strptime(check_in, '%Y-%m-%d')).days)
    
    except requests.exceptions.RequestException as e:
        error_message = f"Error fetching hotel data: {str(e)}"
        return render_template('hotel-results.html', error=error_message, city=city, check_in=check_in, check_out=check_out, selected_currency=currency, total_nights=0)


'''
# Tourist Attraction Suggestions (OpenAI API)
@app.route('/tourist_suggestions', methods=['GET'])
def tourist_suggestions():
    destination = request.args.get('destination')
    prompt = f"List 5 popular tourist attractions in {destination} with a brief description for each."
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",  # Updated endpoint
            json={
                "model": "gpt-3.5-turbo",  # Updated model
                "messages": [
                    {"role": "system", "content": "You are a helpful travel guide."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            },
            headers=headers
        )
        response.raise_for_status()
        result = response.json()
        print(f"OpenAI API response: {result}")  # For debugging
        
        if 'choices' in result and len(result['choices']) > 0:
            return jsonify({"attractions": result['choices'][0]['message']['content'].strip()})
        else:
            return jsonify({"error": "No suggestions found"}), 404
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {str(e)}")  # For debugging
        return jsonify({"error": "Failed to get suggestions. Please try again later."}), 500
'''




# Home Route
@app.route('/')
def index():
    return render_template('index.html')

# Search Route
@app.route('/search')
def search():
    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)
