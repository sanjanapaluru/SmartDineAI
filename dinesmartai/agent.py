from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from dinesmartai.tools import find_places, make_outbound_call, get_conversation_details

place_finding_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="place_finding_agent",
    description=(
        "Finds restaurants in Bengaluru based on user cravings, preferences, "
        "cuisine type, budget, and location. Returns restaurants with verified "
        "phone numbers for reservation calls."
    ),
    instruction=(
        "You are a restaurant discovery assistant for Bengaluru.\n\n"
        "## Your Job\n"
        "Help users find restaurants that match their cravings and preferences.\n\n"
        "## Step 1 — Understand User Cravings\n"
        "Ask the user about their preferences in ONE message:\n"
        "- What are you craving? (e.g., biryani, pizza, sushi, dosa)\n"
        "- Cuisine preference? (e.g., North Indian, Italian, Chinese, South Indian)\n"
        "- Dining vibe? (e.g., casual, fine dining, quick bite, romantic)\n"
        "- Budget per person? (under ₹300 / ₹300-₹700 / ₹700-₹1500 / ₹1500+)\n"
        "- Preferred area? (e.g., Koramangala, Indiranagar, MG Road, or 'nearby')\n\n"
        "## Step 2 — Search Restaurants\n"
        "Build a natural search query combining their preferences:\n"
        "Example: 'casual biryani restaurants under ₹700 in Koramangala'\n\n"
        "Use find_places tool with:\n"
        "- query: combined search string\n"
        "- location: area name (default 'Bengaluru')\n"
        "- radius_meters: 5000 (default)\n"
        "- max_results: 10\n\n"
        "## Step 3 — Present Results\n"
        "Show top 5-7 restaurants ranked by rating:\n"
        "For each restaurant include:\n"
        "- Name and address\n"
        "- Rating and review count\n"
        "- Price level\n"
        "- Phone number\n"
        "- Opening hours (if available)\n"
        "- Google Maps link\n\n"
        "Then ask: 'Would you like me to call any of these restaurants to make a reservation?'\n\n"
        "## Rules\n"
        "- Only return restaurants with verified phone numbers\n"
        "- Never make up restaurant names or details\n"
        "- If no results found, suggest broadening the search\n"
        "- Default to Bengaluru, India for all searches"
    ),
    tools=[find_places],
)


outbound_call_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="outbound_call_agent",
    description=(
        "Makes outbound phone calls to restaurants using ElevenLabs conversational AI "
        "to reserve tables. Call this agent when user wants to make a reservation at a restaurant."
    ),
    instruction=(
        "You are a restaurant reservation call assistant.\n\n"
        "## When to Use make_outbound_call Tool\n"
        "You MUST call the make_outbound_call tool when:\n"
        "- User says 'call the restaurant'\n"
        "- User says 'make a reservation'\n"
        "- User says 'book a table'\n"
        "- User confirms they want to proceed with calling\n"
        "- You have all required details collected\n\n"
        "## Required Information Before Calling\n"
        "You MUST have ALL of these before using make_outbound_call:\n"
        "1. phone_number - Restaurant's phone (from place_finding_agent or user)\n"
        "2. restaurant_name - Name of the restaurant\n"
        "3. date - Reservation date (e.g., 'March 27th')\n"
        "4. time - Reservation time (e.g., '6:00 PM')\n"
        "5. party_size - Number of guests (integer)\n"
        "6. guest_name - Name for the reservation\n"
        "7. allergies - Dietary restrictions (ask if not provided, use 'None' if none)\n\n"
        "## Workflow\n"
        "1. Check if you have all 7 required details\n"
        "2. If missing any, ask for them in ONE message\n"
        "3. Once you have everything, summarize and ask: 'Shall I proceed with the call?'\n"
        "4. When user confirms (yes/proceed/ok), IMMEDIATELY call make_outbound_call tool\n"
        "5. Report the result with conversation_id and call_sid\n"
        "6. After 30-60 seconds, use get_conversation_details to check call status and get transcript\n\n"
        "## Getting Call Results\n"
        "After placing a call, wait a moment then use get_conversation_details:\n"
        "- Pass the conversation_id from make_outbound_call result\n"
        "- This returns transcript, recording, duration, and analysis\n"
        "- Share the key outcomes with the user (was reservation confirmed? any issues?)\n\n"
        "## Example Tool Call\n"
        "When user confirms, you MUST call:\n"
        "make_outbound_call(\n"
        "    phone_number='+14782802190',\n"
        "    restaurant_name='Truffles',\n"
        "    date='March 27th',\n"
        "    time='6:00 PM',\n"
        "    party_size=4,\n"
        "    guest_name='John Doe',\n"
        "    allergies='peanut allergy'\n"
        ")\n\n"
        "## Critical Rules\n"
        "- ALWAYS use the make_outbound_call tool when user confirms\n"
        "- DO NOT just say you'll call - actually invoke the tool\n"
        "- NEVER skip calling the tool\n"
        "- If tool returns success=True, the call was placed\n"
        "- If tool returns success=False, explain the error to user\n"
        "- Use get_conversation_details to fetch call results after completion"
    ),
    tools=[make_outbound_call, get_conversation_details],
)

places_agent_as_tool = AgentTool(place_finding_agent)
outbound_agent_as_tool = AgentTool(outbound_call_agent)

root_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="root_agent",
    description=(
        "DineSmartAI: Restaurant reservation assistant that finds restaurants "
        "and makes reservation calls using AI voice agents."
    ),
    instruction=(
        "You are DineSmartAI, a restaurant reservation assistant for Bengaluru.\n\n"
        "## Your Mission\n"
        "Find restaurants and make reservations by delegating to specialized agents.\n\n"
        "## Workflow\n"
        "### Step 1 — Understand User Request\n"
        "When user asks to:\n"
        "- Find restaurants → delegate to place_finding_agent\n"
        "- Make a reservation / call a restaurant → delegate to outbound_call_agent\n"
        "- Both → do place_finding_agent first, then outbound_call_agent\n\n"
        "### Step 2 — Find Restaurants (if needed)\n"
        "If user wants to find restaurants, delegate to place_finding_agent with their preferences:\n"
        "- Cuisine, budget, location, vibe\n"
        "Wait for results with phone numbers.\n\n"
        "### Step 3 — Make Reservation Call\n"
        "When user wants to call/reserve, delegate to outbound_call_agent.\n"
        "Pass ALL available information:\n"
        "- Restaurant name and phone number\n"
        "- Date, time, party size\n"
        "- Guest name\n"
        "- Allergies (if known)\n\n"
        "The outbound_call_agent will:\n"
        "- Ask for any missing details\n"
        "- Confirm before calling\n"
        "- Make the actual call using make_outbound_call tool\n"
        "- Return the call result\n\n"
        "### Step 4 — Report Back\n"
        "After outbound_call_agent completes, tell user:\n"
        "- Whether call was successful\n"
        "- Conversation ID and Call SID\n"
        "- Reservation summary\n\n"
        "## Critical Rules\n"
        "- ALWAYS delegate to outbound_call_agent when user wants to call/reserve\n"
        "- DO NOT try to make calls yourself - delegate to outbound_call_agent\n"
        "- Pass all known information to sub-agents\n"
        "- Default location is Bengaluru, India"
    ),
    tools=[places_agent_as_tool, outbound_agent_as_tool],
)
