from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pandas as pd
import base64
import os
import re

token_path = 'token.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
client_secret_path = 'client_secret.json'


class ReadInFurnishedFinderHousingRequestsEmails:
    @staticmethod
    def get_emails():
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        service = build('gmail', 'v1', credentials=creds)
        results = service.users().messages().list(
            userId='me',
            q='in:inbox is:unread',
            maxResults=20
        ).execute()
        messages = results.get('messages', [])
        matching_emails = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            headers = payload['headers']
            sender = [header['value'] for header in headers if header['name'] == 'From'][0]
            subject = [header['value'] for header in headers if header['name'] == 'Subject'][0]
            email = re.search(r'<(.*?)>', sender).group(1)
            if email == 'software@venturebnb.io' and 'Traveler Housing Request' in subject:
                matching_emails.append(msg)

        return matching_emails


class PullInformationFromEmailsAndPutIntoDataframe:
    def __init__(self, email_results):
        self.emails_results = email_results

    def get_dataframe(self):
        email_data = self.get_email_data()
        df = pd.DataFrame(list(email_data))
        return df

    def get_email_data(self):
        email_data = []
        for result in self.emails_results:
            payload = result['payload']
            parts = payload.get('parts')
            if 'data' in parts[0]['body'] and 'body' in parts[0]:
                parts_data = parts[0]['body'].get('data', None)
                if parts_data:
                    parts_text = base64.urlsafe_b64decode(parts_data).decode('utf-8')
                    tenant_match = re.search(r'Tenant:\s*([^\s\n].*?)\s*\n', parts_text)
                    if tenant_match:
                        tenant = tenant_match.group(1)
                    else:
                        tenant = None
                    email_match = re.search(r'Email:\s*([^\s\n].*?)\s*\n', parts_text)
                    if email_match:
                        email = email_match.group(1)
                    else:
                        email = None
                    phone_match = re.search(r'Phone #:\s*([^\s\n].*?)\s*\n', parts_text)
                    if phone_match:
                        phone = phone_match.group(1)
                    else:
                        phone = None
                    travelers_match = re.search(r'Travelers:\s*([^\s\n].*?)\s*\n', parts_text)
                    if travelers_match:
                        travelers = travelers_match.group(1)
                    else:
                        travelers = None
                    dates_match = re.search(r'Dates:\s*([^\s\n].*?)\s*\n', parts_text)
                    if dates_match:
                        dates = dates_match.group(1)
                    else:
                        dates = None
                    email_data.append({
                        "tenant": tenant,
                        "email": email,
                        "phone": phone,
                        "travelers": travelers,
                        "dates": dates
                    })

        return email_data


if __name__ == "__main__":
    emails = ReadInFurnishedFinderHousingRequestsEmails.get_emails()
    dataframe = PullInformationFromEmailsAndPutIntoDataframe(emails).get_dataframe()
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    print(dataframe)
