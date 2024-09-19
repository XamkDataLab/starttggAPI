import time
import requests

query="""query{
  tournaments(
    query: {perPage: 3, filter: {past: true, hasOnlineEvents: false, videogameIds: 1386}}
  ) {
    nodes {
      id
      name
      events(filter: {videogameId: 1386}) {
        numEntrants
        type
        sets(sortType: ROUND
        perPage: 5
        
        ) {
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


def run_query(query, header, auto_retry):
    json_request = {'query': query}
    seconds = 10  

    while True:
        try:
            request = requests.post(url='https://api.smash.gg/gql/alpha', json=json_request, headers=header)

            if request.status_code == 400:
                print("Error 400: Bad request (possibly incorrect API key or query syntax)")
                return None
            elif request.status_code == 429:
                print("Error 429: Too many requests, rate limit exceeded")
                if auto_retry:
                    print(f"Retrying in {seconds} seconds...")
                    time.sleep(seconds)
                    seconds *= 2  
                    continue
                else:
                    return None
            elif 400 <= request.status_code < 500:
                print(f"Client Error {request.status_code}: {request.text}")
                return None
            elif 500 <= request.status_code < 600:
                print(f"Server Error {request.status_code}: Please try again later")
                return None
            elif 300 <= request.status_code < 400:
                print(f"Redirection Error {request.status_code}: Unexpected redirection")
                return None

            response = request.json()
            return response

        except requests.exceptions.RequestException as e:
            print(f"Network Error: {e}")
            return None
        
header = {
    "Authorization": "Bearer ba4fe2c4439d5395b736af606c02c2a0",
    "Content-Type": "application/json"
}
response = run_query(query, header, auto_retry=True)

print(response)