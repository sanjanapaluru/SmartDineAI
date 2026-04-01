import asyncio
import os

import googlemaps
from dotenv import load_dotenv
from google.maps import places_v1

load_dotenv()

# ── Geocoding: location name → lat/lng ───────────────────────────────────────


def resolve_lat_lng(location: str) -> tuple[float, float]:
    """
    Convert a location name or address string to (lat, lng)
    using the Google Maps Geocoding API.
    Falls back to Bengaluru city center if geocoding fails.
    """
    try:
        gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_KEY"))
        geocode_result = gmaps.geocode(f"{location}, Bengaluru, India")

        if geocode_result:
            loc = geocode_result[0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
        else:
            print(
                f"[WARN] Could not geocode '{location}'. Falling back to Bengaluru center."
            )
            return 12.9716, 77.5946  # Bengaluru default

    except Exception as e:
        print(f"[ERROR] Geocoding failed: {e}")
        return 12.9716, 77.5946


# ── Validate mandatory fields ─────────────────────────────────────────────────


def validate_place(place: places_v1.Place) -> bool:
    """
    Returns True only if the place has both a display name
    and a national phone number (mandatory business requirement).
    """
    has_name = bool(place.display_name and place.display_name.text.strip())
    has_phone = bool(
        place.national_phone_number and place.national_phone_number.strip()
    )

    if not has_name:
        print(f"[SKIP] Place missing display name — skipping.")
    if not has_phone:
        print(
            f"[SKIP] '{place.display_name.text if place.display_name else '?'}' "
            f"has no phone number — skipping."
        )

    return has_name and has_phone


# ── Core async search ─────────────────────────────────────────────────────────


async def search_places_async(
    query: str,
    location: str,
    radius_meters: float = 5000.0,
    max_results: int = 10,
) -> list[dict]:
    """
    Search for places using Google Places Text Search API.
    Dynamically resolves location to lat/lng via Geocoding API.
    Skips any result that is missing a phone number or display name.
    """

    # Step 1: resolve location to coordinates
    lat, lng = resolve_lat_lng(location)
    print(f"[INFO] Resolved '{location}' → lat={lat}, lng={lng}")

    # Step 2: build Places API client
    client = places_v1.PlacesAsyncClient(
        client_options={"api_key": os.getenv("GOOGLE_MAPS_KEY")}
    )

    # Step 3: build search request with location bias
    request = places_v1.SearchTextRequest(
        text_query=query,
        max_result_count=max_results,
        location_bias=places_v1.SearchTextRequest.LocationBias(
            circle=places_v1.Circle(
                center={"latitude": lat, "longitude": lng},
                radius=radius_meters,
            )
        ),
    )

    # Step 4: include phone number in field mask (mandatory)
    field_mask = (
        "places.displayName,"
        "places.formattedAddress,"
        "places.rating,"
        "places.userRatingCount,"
        "places.priceLevel,"
        "places.websiteUri,"
        "places.nationalPhoneNumber,"  # mandatory
        "places.internationalPhoneNumber,"
        "places.regularOpeningHours,"
        "places.location,"
        "places.googleMapsUri"
    )

    response = await client.search_text(
        request=request,
        metadata=[("x-goog-fieldmask", field_mask)],
    )

    # Step 5: filter and format results
    price_map = {
        0: "Free",
        1: "Inexpensive (₹)",
        2: "Moderate (₹₹)",
        3: "Expensive (₹₹₹)",
        4: "Very Expensive (₹₹₹₹)",
    }

    results = []
    for place in response.places:
        # Skip places missing mandatory fields
        if not validate_place(place):
            continue

        opening_hours = None
        if place.regular_opening_hours:
            opening_hours = {
                "open_now": place.regular_opening_hours.open_now,
                "weekday_text": list(place.regular_opening_hours.weekday_descriptions),
            }

        results.append(
            {
                "name": place.display_name.text,
                "address": place.formatted_address or "N/A",
                "rating": place.rating or "N/A",
                "total_reviews": place.user_rating_count or 0,
                "price_level": price_map.get(place.price_level, "N/A"),
                "phone": place.national_phone_number,  # always present (validated)
                "phone_intl": place.international_phone_number or "N/A",
                "website": place.website_uri or "N/A",
                "google_maps_url": place.google_maps_uri or "N/A",
                "latitude": place.location.latitude if place.location else lat,
                "longitude": place.location.longitude if place.location else lng,
                "opening_hours": opening_hours,
            }
        )

    return results


async def find_places(
    query: str,
    location: str = "Bengaluru",
    radius_meters: float = 5000.0,
    max_results: int = 10,
) -> list[dict]:
    """
    Find restaurants based on user preferences and cravings.
    
    Use this tool to search for restaurants when the user mentions:
    - Food cravings (biryani, pizza, pasta, sushi, etc.)
    - Cuisine types (Indian, Italian, Chinese, etc.)
    - Dining preferences (casual, fine dining, quick bite)
    - Budget constraints (under ₹700, ₹700-₹1500, etc.)
    - Location/area (Koramangala, Indiranagar, etc.)

    Args:
        query: Natural language search combining preferences. 
               Example: 'casual biryani restaurants under ₹700'
        location: Area or neighbourhood name. Default: 'Bengaluru'
                 Example: 'Koramangala', 'Indiranagar', 'MG Road'
        radius_meters: Search radius in meters. Default: 5000
        max_results: Maximum number of results to return. Default: 10

    Returns:
        List of restaurants with name, address, phone, rating, price_level, 
        opening_hours, and google_maps_url. All restaurants have verified phone numbers.
    """
    print(f"[TOOL] find_places called with query='{query}', location='{location}'")
    results = await search_places_async(
        query=query,
        location=location,
        radius_meters=radius_meters,
        max_results=max_results,
    )
    print(f"[TOOL] find_places returned {len(results)} restaurants")
    return results


# ── ElevenLabs Conversational AI ──────────────────────────────────────────────

import httpx


async def make_outbound_call(
    phone_number: str,
    restaurant_name: str,
    date: str,
    time: str,
    party_size: int,
    guest_name: str,
    allergies: str = "None",
) -> dict:
    """
    Make an outbound phone call to a restaurant to reserve a table.
    
    USE THIS TOOL when the user confirms they want to make a reservation call.
    This tool will actually place a real phone call using ElevenLabs AI.
    
    Args:
        phone_number: Restaurant's phone number in E.164 format (e.g., '+919876543210' or '+14782802190')
        restaurant_name: Full name of the restaurant (e.g., 'Truffles', 'The Black Pearl')
        date: Reservation date in natural language (e.g., 'March 27th', 'tomorrow', 'Friday')
        time: Reservation time (e.g., '6:00 PM', '7:30 PM', '8 PM')
        party_size: Number of guests as integer (e.g., 2, 4, 6, 8)
        guest_name: Name for the reservation (e.g., 'John Smith', 'Priya Kumar')
        allergies: Dietary allergies or restrictions (e.g., 'peanut allergy', 'vegetarian', 'gluten-free', 'None')
    
    Returns:
        dict: Call result with success status, conversation_id, call_sid, and reservation summary
        
    Example:
        result = await make_outbound_call(
            phone_number="+14782802190",
            restaurant_name="Truffles",
            date="March 27th",
            time="6:00 PM",
            party_size=4,
            guest_name="John Doe",
            allergies="peanut allergy"
        )
    """
    print(f"\n{'='*70}")
    print(f"[TOOL CALLED] make_outbound_call() has been invoked!")
    print(f"{'='*70}")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")
    phone_number_id = os.getenv("ELEVENLABS_PHONE_NUMBER_ID")
    
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment")
    if not agent_id:
        raise ValueError("ELEVENLABS_AGENT_ID not found in environment. Add your agent ID to .env")
    if not phone_number_id:
        raise ValueError("ELEVENLABS_PHONE_NUMBER_ID not found in environment. Add your Twilio phone number ID to .env")
    
    # Format phone number to E.164 if needed
    if not phone_number.startswith("+"):
        phone_number = f"+91{phone_number}"
    
    # Pass reservation details as dynamic_variables (no security override required).
    # The agent's base prompt in the ElevenLabs dashboard should reference these
    # variables using {{variable_name}} placeholders.
    reservation_context = {
        "dynamic_variables": {
            "restaurant_name": restaurant_name,
            "reservation_date": date,
            "reservation_time": time,
            "party_size": str(party_size),
            "guest_name": guest_name,
            "dietary_restrictions": allergies,
        }
    }
    
    url = "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    
    payload = {
        "agent_id": agent_id,
        "agent_phone_number_id": phone_number_id,
        "to_number": phone_number,
        "conversation_initiation_client_data": reservation_context,
    }
    
    print(f"\n[INFO] ========== MAKING OUTBOUND CALL ==========")
    print(f"[INFO] Restaurant: {restaurant_name}")
    print(f"[INFO] Phone: {phone_number}")
    print(f"[INFO] Date: {date} at {time}")
    print(f"[INFO] Party size: {party_size}")
    print(f"[INFO] Guest name: {guest_name}")
    print(f"[INFO] Allergies: {allergies}")
    print(f"[INFO] Agent ID: {agent_id}")
    print(f"[INFO] Phone Number ID: {phone_number_id}")
    print(f"[INFO] API URL: {url}")
    print(f"[INFO] Payload: {payload}")
    print(f"[INFO] ==========================================\n")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"[INFO] Sending POST request to ElevenLabs...")
            response = await client.post(url, headers=headers, json=payload)
            
            print(f"[INFO] Response Status Code: {response.status_code}")
            print(f"[INFO] Response Headers: {dict(response.headers)}")
            print(f"[INFO] Response Body: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            print(f"\n[SUCCESS] ✓ Call placed successfully!")
            print(f"[SUCCESS] Conversation ID: {data.get('conversation_id')}")
            print(f"[SUCCESS] Call SID: {data.get('callSid')}")
            print(f"[SUCCESS] Message: {data.get('message')}")
            
            return {
                "success": data.get("success", True),
                "conversation_id": data.get("conversation_id"),
                "call_sid": data.get("callSid"),
                "phone_number": phone_number,
                "restaurant": restaurant_name,
                "reservation_summary": (
                    f"{party_size} guests on {date} at {time} "
                    f"under {guest_name}. Allergies: {allergies}"
                ),
                "status": "Call initiated successfully",
                "message": data.get("message", "Success"),
            }
    except httpx.ReadTimeout:
        print("[ERROR] ElevenLabs API request timed out")
        return {
            "success": False,
            "error": "API timeout - please try again",
            "phone_number": phone_number,
            "restaurant": restaurant_name,
        }
    except httpx.HTTPStatusError as e:
        error_text = e.response.text if hasattr(e.response, 'text') else str(e)
        print(f"[ERROR] ✗ ElevenLabs API error: {e.response.status_code}")
        print(f"[ERROR] Response: {error_text}")
        return {
            "success": False,
            "error": f"API error {e.response.status_code}: {error_text}",
            "phone_number": phone_number,
            "restaurant": restaurant_name,
        }
    except Exception as e:
        print(f"[ERROR] ✗ Failed to make call: {e}")
        return {
            "success": False,
            "error": str(e),
            "phone_number": phone_number,
            "restaurant": restaurant_name,
        }



async def get_conversation_details(conversation_id: str) -> dict:
    """
    Get details and transcript of a completed conversation/call.
    
    USE THIS TOOL after a call is completed to get the conversation transcript,
    recording, and analysis of what happened during the call.
    
    Args:
        conversation_id: The conversation ID returned from make_outbound_call
    
    Returns:
        dict: Conversation details including transcript, status, duration, and analysis
        
    Example:
        result = await get_conversation_details(
            conversation_id="conv_7401kmpvav63ev4b5vj9fd514wa7"
        )
    """
    print(f"\n{'='*70}")
    print(f"[TOOL CALLED] get_conversation_details() has been invoked!")
    print(f"[INFO] Conversation ID: {conversation_id}")
    print(f"{'='*70}\n")
    
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY not found in environment")
    
    url = f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}"
    headers = {"xi-api-key": api_key}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"[INFO] Fetching conversation details...")
            response = await client.get(url, headers=headers)
            
            print(f"[INFO] Response Status Code: {response.status_code}")
            print(f"[INFO] Response Body: {response.text[:500]}...")
            
            response.raise_for_status()
            data = response.json()
            
            # Extract key information — field names match the actual API response shape
            metadata = data.get("metadata", {}) or {}
            analysis = data.get("analysis", {}) or {}
            transcript_entries = data.get("transcript", []) or []
            
            conversation_info = {
                "conversation_id": data.get("conversation_id"),
                "agent_id": metadata.get("agent_id") or data.get("agent_id"),
                "status": metadata.get("call_successful") or data.get("status"),
                "termination_reason": metadata.get("termination_reason", ""),
                "start_time_unix": metadata.get("start_time_unix_secs"),
                "call_duration_secs": metadata.get("call_duration_secs"),
                "transcript": [
                    {"role": t.get("role"), "message": t.get("message")}
                    for t in transcript_entries
                ],
                "transcript_summary": analysis.get("transcript_summary"),
                "call_successful": analysis.get("call_successful"),
                "evaluation": analysis.get("evaluation_criteria_results", {}),
                "collected_data": analysis.get("data_collection_results", {}),
                "has_audio": data.get("has_audio", False),
                "has_user_audio": data.get("has_user_audio", False),
            }
            
            print(f"\n[SUCCESS] ✓ Conversation details retrieved!")
            print(f"[SUCCESS] Call duration: {conversation_info['call_duration_secs']} seconds")
            print(f"[SUCCESS] Termination reason: {conversation_info['termination_reason']}")
            print(f"[SUCCESS] Transcript entries: {len(conversation_info['transcript'])}")
            
            return conversation_info
            
    except httpx.HTTPStatusError as e:
        error_text = e.response.text if hasattr(e.response, 'text') else str(e)
        print(f"[ERROR] ✗ API error: {e.response.status_code}")
        print(f"[ERROR] Response: {error_text}")
        return {
            "success": False,
            "error": f"API error {e.response.status_code}: {error_text}",
            "conversation_id": conversation_id,
        }
    except Exception as e:
        print(f"[ERROR] ✗ Failed to get conversation: {e}")
        return {
            "success": False,
            "error": str(e),
            "conversation_id": conversation_id,
        }
