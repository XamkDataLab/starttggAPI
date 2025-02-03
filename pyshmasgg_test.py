import time
import requests
import pandas as pd

# Updated GraphQL query with additional fields and parameters.
query_template = """query($page: Int!, $perPage: Int!){
  tournaments(
    query: {perPage: $perPage, page: $page, filter: {past: true, hasOnlineEvents: false, videogameIds: 1386}}
  ) {
    pageInfo {
      totalPages
      total
    }
    nodes {
      id
      name
      events(filter: {videogameId: 1386}) {
        numEntrants
        type
        sets(sortType: ROUND, perPage: $perPage) {  
          nodes {
            games {
              winnerId
              selections {
                character {
                  name
                }
                entrant {
                  id
                  seeds {
                    seedNum
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""

# Function to execute the GraphQL query with error handling and optional retry logic
def run_query(query, variables, headers, auto_retry=True):
    json_request = {'query': query, 'variables': variables}
    seconds = 10  # Initial retry delay time

    while True:
        try:
            request = requests.post(
                url='https://api.smash.gg/gql/alpha', 
                json=json_request, 
                headers=headers
            )

            if request.status_code == 400:
                print("Error 400: Bad request (incorrect API key or query syntax)")
                return None
            elif request.status_code == 429:
                print("Error 429: Too many requests, rate limit exceeded")
                if auto_retry:
                    print(f"Retrying in {seconds} seconds...")
                    time.sleep(seconds)
                    seconds *= 2  # Exponential backoff
                    continue
                else:
                    return None
            elif 400 <= request.status_code < 500:
                print(f"Client Error {request.status_code}: {request.text}")
                return None
            elif 500 <= request.status_code < 600:
                print(f"Server Error {request.status_code}: Please try again later")
                return None

            response = request.json()

            if "errors" in response:
                print(f"GraphQL Error: {response['errors']}")
                return None

            return response

        except requests.exceptions.RequestException as e:
            print(f"Network Error: {e}")
            return None

# API Header with authentication token
header = {
    "Authorization": "myAPIkey",
    "Content-Type": "application/json"
}

# Pagination logic: fetch all tournaments and add new variables (entrant IDs and seeds) to the DataFrame.
def fetch_all_tournaments(per_page=5, max_pages=5):
    page = 1
    tournaments_list = []

    while page <= max_pages:
        print(f"\nFetching page {page}...")

        variables = {"page": page, "perPage": per_page}
        response = run_query(query_template, variables, header)

        if not response or "data" not in response or "tournaments" not in response["data"]:
            print("No response from API or invalid format.")
            break

        tournaments = response["data"]["tournaments"]["nodes"]

        if not tournaments:
            print("No tournaments found.")
            break

        # Process each tournament
        for t in tournaments:
            tournament_id = t.get("id")
            name = t.get("name")
            events = t.get("events", [])
            for event in events:
                num_entrants = event.get("numEntrants")
                event_type = event.get("type")
                sets = event.get("sets", {}).get("nodes", [])
                
                # Process each set within the event
                for s in sets:
                    games = s.get("games")
                    if not isinstance(games, list):
                        tournaments_list.append({
                            "Tournament ID": tournament_id,
                            "Tournament Name": name,
                            "Num Entrants": num_entrants,
                            "Event Type": event_type,
                            "Winner ID": None,
                            "Characters Used": None,
                            "Entrant IDs": None,
                            "Seeds": None
                        })
                        continue

                    # Process each game within the set
                    for g in games:
                        winner_id = g.get("winnerId")
                        selections = g.get("selections")

                        if not isinstance(selections, list):
                            tournaments_list.append({
                                "Tournament ID": tournament_id,
                                "Tournament Name": name,
                                "Num Entrants": num_entrants,
                                "Event Type": event_type,
                                "Winner ID": winner_id,
                                "Characters Used": "Unknown",
                                "Entrant IDs": "Unknown",
                                "Seeds": "Unknown"
                            })
                        else:
                            # Gather data from all selections in the game
                            character_names = [
                                sel.get("character", {}).get("name", "Unknown")
                                for sel in selections
                            ]
                            entrant_ids = [
                                str(sel.get("entrant", {}).get("id", "Unknown"))
                                for sel in selections
                            ]
                            seeds_list = []
                            for sel in selections:
                                seeds = sel.get("entrant", {}).get("seeds", [])
                                if isinstance(seeds, list) and seeds:
                                    seed_nums = [
                                        str(seed.get("seedNum", "Unknown"))
                                        for seed in seeds
                                    ]
                                    seeds_list.append(", ".join(seed_nums))
                                else:
                                    seeds_list.append("None")
    
                            tournaments_list.append({
                                "Tournament ID": tournament_id,
                                "Tournament Name": name,
                                "Num Entrants": num_entrants,
                                "Event Type": event_type,
                                "Winner ID": winner_id,
                                "Characters Used": ", ".join(character_names),
                                "Entrant IDs": ", ".join(entrant_ids),
                                "Seeds": ", ".join(seeds_list)
                            })

        total_pages = response["data"]["tournaments"]["pageInfo"]["totalPages"]
        print(f"Total Pages: {total_pages}, Current Page: {page}")

        if page >= total_pages:
            break  # Exit if this is the last page

        page += 1  # Move to the next page

    # Convert the collected tournament data to a DataFrame
    df = pd.DataFrame(tournaments_list)
    return df

# Fetch tournaments with the updated query and DataFrame including new variables.
tournaments_df = fetch_all_tournaments(per_page=5, max_pages=15)
tournaments_df
