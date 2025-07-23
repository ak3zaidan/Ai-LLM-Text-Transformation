from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import json
import re

GPT_API_KEY = "..."

app = Flask(__name__)
CORS(app)

# CORS(app, origins=["https://yourdomain.com"])

directions_variants = {
    "SW": ["SW", "Southwest", "South West", "S.W.", "SouthW", "S W", "S-W"],
    "NW": ["NW", "Northwest", "North West", "N.W.", "NorthW", "N W", "N-W"],
    "SE": ["SE", "Southeast", "South East", "S.E.", "SouthE", "S E", "S-E"],
    "NE": ["NE", "Northeast", "North East", "N.E.", "NorthE", "N E", "N-E"],
    "N":  ["N", "North", "N.", "Nrth", "Nth", "Nt", "N "],
    "S":  ["S", "South", "S.", "Sth", "St", "So", "S "],
    "E":  ["E", "East", "E.", "Est", "Ea", "E "],
    "W":  ["W", "West", "W.", "Wst", "Wt", "We", "W "]
}

suffixes_variants = {
    "LN": ["LN", "Lane", "Lanne", "Ln.", "Laine", "Lain", "Lne"],
    "ST": ["ST", "Street", "Strt", "St.", "Str", "Steet", "Stret", "Strt.", "Str."],
    "RD": ["RD", "Road", "Rode", "Rd.", "Rod", "Roadd", "Rd"],
    "DR": ["DR", "Drive", "Dr.", "Driv", "Drve", "Dr."],
    "BLVD": ["BLVD", "Boulevard", "Blvd.", "Boulvard", "Boulv", "Blv"],
    "AVE": ["AVE", "Avenue", "Av.", "Aven", "Avn", "Avnue"],
    "CT": ["CT", "Court", "Ct.", "Cort", "Crt"],
    "PL": ["PL", "Place", "Pl.", "Pla", "Plc"],
    "TER": ["TER", "Terrace", "Ter.", "Terr", "Trce"],
    "CIR": ["CIR", "Circle", "Cir.", "Crcle", "Circ"],
    "HWY": ["HWY", "Highway", "Hwy.", "Hiway", "Hghwy"],
    "PKWY": ["PKWY", "Parkway", "Pkwy.", "Parkwy", "Parkway"],
    "SQ": ["SQ", "Square", "Sq.", "Squar", "Sqr"],
    "WAY": ["WAY", "Way", "Wy.", "Wey", "Wa"],
    "LOOP": ["Loop", "Lp", "Loop.", "Loopp"],
    "EXPY": ["EXPY", "Expressway", "Expy", "Exprsswy"],
    "TRL": ["TRL", "Trail", "Trl.", "Trail.", "Trai"],
}

def make_bidirectional_map(variants_dict):
    bi_map = {}
    for canonical, variants in variants_dict.items():
        for v in variants:
            bi_map[v.lower()] = canonical
    return bi_map

directions_map = make_bidirectional_map(directions_variants)
suffixes_map = make_bidirectional_map(suffixes_variants)

def replace_word(word, bi_map, variants_dict):
    low = word.lower()
    if low in bi_map:
        canonical = bi_map[low]
        variants = variants_dict[canonical]
        replacement = random.choice(variants)
        # Preserve capitalization style
        if word.istitle():
            return replacement.title()
        elif word.isupper():
            return replacement.upper()
        else:
            return replacement
    return word

def manual_jig_address(address: str, count: int):
    results = set()
    attempts = 0

    while len(results) < count and attempts < count * 10:
        words = address.split()
        jiggled_words = []
        for w in words:
            # Try directions first
            new_w = replace_word(w, directions_map, directions_variants)
            if new_w == w:
                # Try suffixes second
                new_w = replace_word(w, suffixes_map, suffixes_variants)
            jiggled_words.append(new_w)

        # Optionally add a unit/suite number randomly to about half of the addresses
        jigged_address = " ".join(jiggled_words)
        if random.random() < 0.5:
            unit_prefix = random.choice(["Unit", "Apt", "Suite", "#"])
            unit_number = random.randint(1, 99)
            jigged_address = f"{jigged_address} {unit_prefix} {unit_number}"

        results.add(jigged_address.strip())
        attempts += 1

    return list(results)

@app.route("/", methods=["POST"])
def jig():
    data = request.get_json()

    address = data.get("address")
    if not address:
        return jsonify({"error": "Missing 'address'"}), 400

    count = data.get("count")
    if not isinstance(count, int) or count <= 0:
        return jsonify({"error": "'count' must be a positive integer"}), 400

    if count > 25:
        count = 25

    PROMPT = f"""
    Jig the address below {count} times. Only return the randomized addresses as a JSON string array.

    Address: "{address}"

    Example format:
    ["Address jigged 1", "Address jigged 2", ...]

    Extra context:
    Jigging refers to modifying an address in a way that makes each version appear unique or random, but all versions must still refer to the same location (e.g., altering abbreviations, adjusting punctuation, etc.).
    """

    headers = {
        "Authorization": f"Bearer {GPT_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": PROMPT.strip()}],
        "temperature": 0.7
    }

    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        reply_text = response.json()["choices"][0]["message"]["content"]

        jigs = extract_array(reply_text)
        if jigs:
            jigs = [jig.replace(',', '') for jig in jigs]
            
            return jsonify({"jigs": jigs, "source": "ai"}), 200
        else:
            # Fallback to manual jigging if parsing fails
            fallback_jigs = manual_jig_address(address, count)
            return jsonify({"jigs": fallback_jigs, "source": "fallback"}), 200

    except requests.exceptions.RequestException as e:
        # Fallback to manual jigging if parsing fails
        fallback_jigs = manual_jig_address(address, count)
        return jsonify({"jigs": fallback_jigs, "source": "fallback"}), 200

def extract_array(text: str):
    """
    Try multiple extraction methods to extract a string array from the OpenAI response.
    Returns list[str] or None.
    """

    # Method 1: Regex match for any array
    array_match = re.search(r'\[[^\]]*\]', text, re.DOTALL)
    if array_match:
        try:
            arr = json.loads(array_match.group(0))
            if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
                return arr
        except json.JSONDecodeError:
            pass

    # Method 2: Strip markdown code blocks and parse what's inside
    code_block_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, re.IGNORECASE)
    if code_block_match:
        try:
            arr = json.loads(code_block_match.group(1))
            if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
                return arr
        except json.JSONDecodeError:
            pass

    # Method 3: Line-by-line JSON-looking array
    lines = text.strip().splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            try:
                arr = json.loads(line)
                if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
                    return arr
            except json.JSONDecodeError:
                continue

    # Method 4: Manually build array from lines
    try:
        start_index = text.index("[")
        end_index = text.rindex("]") + 1
        possible_json = text[start_index:end_index]
        arr = json.loads(possible_json)
        if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
            return arr
    except (ValueError, json.JSONDecodeError):
        pass

    return None

def main(request):
    # Call Flask app
    response = app(request.environ, lambda status, headers: None)

    # Manually add CORS headers
    from flask import make_response
    flask_response = make_response(response)
    flask_response.headers["Access-Control-Allow-Origin"] = "*"
    flask_response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    flask_response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    # Handle preflight requests (OPTIONS)
    if request.method == "OPTIONS":
        return flask_response, 204

    return flask_response
