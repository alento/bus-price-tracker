import requests
import json
import re
import datetime
import csv
import time
import os
try: 
    session = requests.Session()
    url = "https://www.cleartrip.com/bus/results"
    params = {
        'fromCity': '8902',
        'toCity': '19191',
        'journeyDate': '2026-07-09',
        'fromCityName': 'Bangalore',
        'toCityName': 'Thiruvananthapuram',
        # '_rsc': 'gocxn',   # keep this (important)
    }    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': '*/*',
        'Referer': 'https://www.cleartrip.com/bus',
        'rsc': '1',
        'next-url': '/bus',
    }
    # Adding Warm-up requests
    session.get("https://www.cleartrip.com/", timeout=10)
    session.get("https://www.cleartrip.com/bus", timeout=10)
    
    # Creating Retry logic function for reliability    
    def fetch_data(session, url, params, headers):
        for attempt in range(3):
            try:
                session.headers.update(headers)
                response = session.get(url, params=params, timeout=10)
                print(response.text[:500])
                # Detect if API breaks silently
               # if "<!DOCTYPE html>" in response.text:
               #     raise Exception("Blocked (HTML response)")
              #  if '"response":' not in response.text:
              #      raise Exception("Invalid response structure")
                return response.text
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1} failed: {e}")
                time.sleep(5)
        raise Exception("❌ All retries failed")
        
    #Invoke retry function
    raw_text = fetch_data(session, url, params, headers)
    
    # Extract response JSON
    start = raw_text.find('"response":')
    
    #Check if a JSON text response was received
    if start == -1:
        print("❌ Could not find response JSON")
        exit()
        
    #Finds the first { AFTER "response"
    brace_start = raw_text.find("{", start)
    
    # Raise exception if "{" not found after response
    if brace_start == -1:
        raise Exception("JSON start not found")
        
    brace_count = 0
    end = brace_start
    
    for i in range(brace_start, len(raw_text)):
        if raw_text[i] == "{":
            brace_count += 1
        elif raw_text[i] == "}":
            brace_count -= 1
        if brace_count == 0:
            end = i + 1
            break
    #Check if JSON text is malformed with missing braces
    if brace_count != 0:
        raise Exception("JSON extraction failed — unmatched braces")
        
    #Store JSON text
    json_text = raw_text[brace_start:end]
    
    #Convert to JSON
    data = json.loads(json_text)
    
    #Access buses
    buses = data["data"]["buses"]
    
    #Load Existing Data
    existing_data = {}
    if os.path.isfile("bus_prices.csv"):
         with open("bus_prices.csv", "r") as f:
             reader = csv.reader(f)
             next(reader, None)  # skip header
             for row in reader:
                 solution_id = row[1]
                 price = row[4]
                 seats = row[5]
                 existing_data[solution_id] = (price, seats)
                 
    #Save to CSV
    stored_count = 0
    file_exists = os.path.isfile("bus_prices.csv")
    with open("bus_prices.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["time","solutionId","operator","departure","price","seats"])
        for bus in buses:
            try:
                fares = bus.get("fares", [])
                valid_prices = [f.get("total") for f in fares if f.get("total") is not None]
                
                if not valid_prices:
                    continue
                    
                price = str(min(valid_prices))   # convert to string for comparison
                seats = str(bus.get("availableSeats"))
                solution_id = str(bus.get("solutionId"))
                
                # Deduplication check
                if solution_id in existing_data:
                    old_price, old_seats = existing_data[solution_id]                 
                    # skip duplicate
                    if old_price == price and old_seats == seats:
                        continue
                    
                # Write only if changed                
                writer.writerow([
                	datetime.datetime.now(),
                	solution_id,
                	bus.get("meta", {}).get("operatorName", "NA"),
                	bus.get("deptTime"),
                	price,
                	seats
                ])
                stored_count += 1
            except Exception as e:
                print("⚠️ Error processing bus:", e)
                continue
    # Summary of extracted data
    print(f"✅ Found {len(buses)} buses at {datetime.datetime.now()}")
    print(f"✅ Stored {stored_count} updates at {datetime.datetime.now()}")
except Exception as e:
    print("❌ Fatal error:", e)
    with open("error.log", "a") as f:
        f.write(f"{datetime.datetime.now()} - {str(e)}\n")
