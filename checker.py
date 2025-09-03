import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# Your Slack webhook URL (you'll replace this with your actual one)
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', 'YOUR_WEBHOOK_URL_HERE')

def get_layoff_companies():
    """Fetch the current list of companies from layoffs.fyi"""
    try:
        # Get the webpage
        response = requests.get('https://layoffs.fyi/')
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all company entries (they're in table rows)
        companies = []
        
        # Look for the main table with layoff data
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:  # Make sure we have company and date
                    company_name = cells[0].get_text(strip=True)
                    layoff_date = cells[1].get_text(strip=True) if len(cells) > 1 else "Unknown date"
                    
                    if company_name and company_name not in ['Company', '']:  # Skip headers
                        companies.append({
                            'name': company_name,
                            'date': layoff_date,
                            'full_row': row.get_text(strip=True)[:200]  # First 200 chars of the row
                        })
        
        return companies
    
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def load_seen_companies():
    """Load the list of companies we've already seen"""
    try:
        if os.path.exists('seen_companies.json'):
            with open('seen_companies.json', 'r') as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_seen_companies(companies):
    """Save the list of companies we've seen"""
    with open('seen_companies.json', 'w') as f:
        json.dump(list(companies), f)

def send_slack_notification(new_companies):
    """Send a message to Slack about new companies"""
    if not new_companies:
        return
    
    # Create the message
    message = {
        "text": f"🚨 New Layoffs Detected on layoffs.fyi",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚨 {len(new_companies)} New {'Company' if len(new_companies) == 1 else 'Companies'} Added to Layoff Tracker*"
                }
            },
            {
                "type": "divider"
            }
        ]
    }
    
    # Add each company
    for company in new_companies[:10]:  # Limit to 10 to avoid huge messages
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"• *{company['name']}*\n  Date: {company['date']}\n  Details: {company['full_row'][:100]}..."
            }
        })
    
    if len(new_companies) > 10:
        message["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"_...and {len(new_companies) - 10} more companies_"
            }
        })
    
    # Add link to the website
    message["blocks"].append({
        "type": "divider"
    })
    message["blocks"].append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "View all details at <https://layoffs.fyi/|layoffs.fyi>"
        }
    })
    
    # Send to Slack
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print(f"Successfully sent notification for {len(new_companies)} new companies")
    except Exception as e:
        print(f"Error sending to Slack: {e}")

def main():
    print(f"Checking layoffs.fyi at {datetime.now()}")
    
    # Get current companies
    current_companies = get_layoff_companies()
    print(f"Found {len(current_companies)} total companies")
    
    # Load previously seen companies
    seen_companies = load_seen_companies()
    print(f"Previously tracked {len(seen_companies)} companies")
    
    # Find new companies
    current_company_names = {c['name'] for c in current_companies}
    new_company_names = current_company_names - seen_companies
    
    if new_company_names:
        print(f"Found {len(new_company_names)} new companies!")
        
        # Get full details for new companies
        new_companies = [c for c in current_companies if c['name'] in new_company_names]
        
        # Send notification
        send_slack_notification(new_companies)
        
        # Update seen companies
        save_seen_companies(current_company_names)
    else:
        print("No new companies found")
    
    print("Check complete!")

if __name__ == "__main__":
    main()
