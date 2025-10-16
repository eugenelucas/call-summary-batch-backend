import requests
import os
from urllib.parse import urlparse, parse_qs
import json
class ServiceNowPDFUploader:
    def __init__(self, instance_url, access_token):
        self.instance_url = instance_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        })
    
    def extract_sys_id_from_url(self, ui_url):
        """Extract sys_id from ServiceNow UI URL"""
        parsed = urlparse(ui_url)
        params = parse_qs(parsed.query)
        
        # sys_id can be in the query parameters
        if 'sys_id' in params:
            return params['sys_id'][0]
        
        # Sometimes it's in the path for newer UI
        if 'sys_id=' in ui_url:
            start = ui_url.find('sys_id=') + 7
            end = ui_url.find('&', start)
            if end == -1:
                return ui_url[start:]
            return ui_url[start:end]
        
        return None
    
    def upload_feedback_file(self, incident_sys_id: str, feedback: str, rate: str, as_json=True):
        """
        Create and upload a feedback file (JSON or TXT) to the incident.
        Example:
            uploader.upload_feedback_file(sys_id, "stress site", "good", as_json=True)
        """
        url = f"{self.instance_url}/api/now/attachment/file"
        filename = "feedback.json" if as_json else "feedback.txt"

        # Prepare content
        if as_json:
            file_content = json.dumps({"rate": rate, "feedback": feedback}, indent=2)
            content_type = "application/json"
        else:
            file_content = f"Rate: {rate}\nFeedback: {feedback}"
            content_type = "text/plain"

        params = {
            "table_name": "incident",
            "table_sys_id": incident_sys_id,
            "file_name": filename
        }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Content-Type": content_type
        }

        response = self.session.post(
            url,
            params=params,
            headers=headers,
            data=file_content.encode("utf-8")
        )

        if response.status_code == 201:
            print(f"✓ Successfully uploaded {filename} to incident")
            return response.json()
        else:
            print(f"✗ Failed to upload feedback: {response.status_code}")
            print(f"Response: {response.text}")
            return {"error": "feedback upload failed", "status_code": response.status_code}

    def upload_pdf_to_incident(self, incident_sys_id, pdf_file_path, custom_filename=None):
        """Upload PDF to incident using sys_id"""
        if not os.path.exists(pdf_file_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_file_path}")
        
        # Determine filename
        filename = custom_filename if custom_filename else os.path.basename(pdf_file_path)
        
        # Use the REST API endpoint (not the .do endpoint)
        url = f"{self.instance_url}/api/now/attachment/file"
        
        # Parameters for the attachment
        params = {
            'table_name': 'incident',
            'table_sys_id': incident_sys_id,
            'file_name': filename
        }
        
        # Headers
        headers = {
            'Content-Type': 'application/pdf',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        # Upload file
        with open(pdf_file_path, 'rb') as pdf_file:
            response = self.session.post(
                url,
                params=params,
                headers=headers,
                data=pdf_file.read()
            )
        
        if response.status_code == 201:
            print(f"✓ Successfully uploaded {filename} to incident")
            return response.json()
        elif response.status_code == 404:
            print(f"✗ Incident with sys_id {incident_sys_id} not found")
            # Try to get incident details
            self.verify_incident_exists(incident_sys_id)
            return {"error" : "incident not found."}
        elif response.status_code == 401:
            print("✗ Authentication failed. Check your access token.")
            return {"error" : "token error"}
        else:
            print(f"✗ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
            return {"error" : "upload failed"}
        
        return None
    
    def verify_incident_exists(self, sys_id):
        """Verify if incident exists and get its details"""
        url = f"{self.instance_url}/api/now/table/incident/{sys_id}"
        
        response = self.session.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                incident = data['result']
                print(f"\nIncident found:")
                print(f"  Number: {incident.get('number', 'N/A')}")
                print(f"  Short Description: {incident.get('short_description', 'N/A')}")
                print(f"  State: {incident.get('state', 'N/A')}")
                return True
        else:
            print(f"\nCould not find incident with sys_id: {sys_id}")
            print("Please verify the sys_id is correct.")
            return False
    
    def upload_pdf_from_ui_url(self, ui_url, pdf_file_path, custom_filename=None):
        """Upload PDF using a ServiceNow UI URL"""
        # Extract sys_id from URL
        sys_id = self.extract_sys_id_from_url(ui_url)
        
        if not sys_id:
            raise ValueError("Could not extract sys_id from URL")
        
        print(f"Extracted sys_id: {sys_id}")
        
        # Upload the PDF
        return self.upload_pdf_to_incident(sys_id, pdf_file_path, custom_filename)


def get_incident_sys_id(instance_url: str, token: str, inc_number: str) -> str:
    """
    Query ServiceNow to get sys_id for given INC number
    """
    url = f"{instance_url}/api/now/table/incident"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    params = {"number": inc_number}

    try:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 200:
            result = resp.json().get("result", [])
            if result and len(result) > 0:
                return result[0]["sys_id"]
        print(f"Failed to get sys_id for {inc_number}: {resp.text}")
        return None
    except Exception as e:
        print(f"Error fetching sys_id: {e}")
        return None


def get_servicenow_access_token():
    """
    Get ServiceNow OAuth access token
    Returns: access token string or None if failed
    """
    url = "https://franciscanalliancepoc.service-now.com/oauth_token.do"
    
    # Use the exact payload from Postman (already URL encoded)
    payload = {
        "grant_type": "password",
        "client_id": "01edacb178164926b5e7de3d9f33cd22",
        "client_secret": "-4@dz2D<J-",
        "username": "XSNELEVANCEPOC",
        "password": "-{&C{ko.}=0x8f<RPi};U.IIoJ;Qecz0WMEf8]}qO@>1NgRZjY>OvHoV>,4I0dAQ9f!dDr0qSd0oG_Xs=(,,f^gUCCog4:9.*o:9"
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        
        if response.status_code == 200:
            response_json = response.json()
            return response_json.get("access_token")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error: {e}")
        return None
     