from flask import Flask, request
from copy import deepcopy
import twilio.twiml
from twilio.rest import TwilioRestClient
from datetime import datetime, timedelta
import pytz
import re

class AccessManager(object):
    def __init__(self):
        self.admin_users = {}
        self.permissions = {} #'+17787075262': datetime.now() + timedelta(seconds=120)} 
        self.door_numbers = []
        self.access_pin ='1234'
        self.primary_number = None

    def add_admin(self, name, number, is_primary=False):
        self.admin_users[name] = number
        if is_primary:
            self.primary_number = number

    def add_door_number(self, number):
        self.door_numbers.append(number)

    def process_instruction(self, from_number, message):
        if from_number not in self.admin_users.values():
            return {"accepted": False, "reply": "Access denied"}

        print "Message: '%s', Type: %s" % (message, type(message))
        if message.lower().startswith('open for '):
            matches = re.findall('\b*\d+$', message)
            if matches and len(matches) > 0 and matches[-1] >= 0:
                expiry = self.calculate_expiry(int(matches[-1]) * 60)
                date_str = self.authorize(from_number, expiry)
                return {"accepted": True, "reply": "Confirmed. Valid till %s" % date_str}

        elif message.lower().strip() == "clear permissions":
            self.clear_permissions()
            return {"accepted": True, "reply": "Permissions Cleared"}
        elif message.lower().startswith('set pin '):
            matches = re.findall('\b*\d+$', message)
            if matches and len(matches) > 0 and matches[-1] >= 0:
                print "Setting access PIN: %s" % str(matches[-1])
                self.access_pin = str(matches[-1])
                return {"accepted": True, "reply": "PIN set successfully"}
            else:
                return {"accepted": False, "reply": "Invalid command"}
        elif message.lower().strip() == 'clear pin':
            print "Clearing access PIN"
            self.access_pin = None
            return {"accepted": True, "reply": "PIN cleared"}
        else:
            return {"accepted": False, "reply": "Unknown Instruction"}

    def check_permissions(self):
        tmp_permissions = deepcopy(self.permissions)
        time_now = datetime.now()
        for number, expiry in tmp_permissions.iteritems():
            if time_now > expiry:
                print "Deleting expired permission"
                self.permissions.pop(number)
        return self.permissions

    def calculate_expiry(self, secs):
       return datetime.now() + timedelta(seconds=secs)

    def authorize(self, number, expiry):
        print "Adding permissions: %s" % (self.format_dt(expiry))
        self.permissions[number] = expiry
        date_str = self.format_dt(expiry)
        return date_str

    def format_dt(self, dt):
        dt = dt.replace(tzinfo=pytz.timezone('UTC'))
        tz = pytz.timezone('US/Pacific')
        return dt.astimezone(tz).strftime("%H:%M:%S %Z")
    
    def clear_permissions(self):
        print "Clearing all permissions"
        self.permissions = {}

    def is_valid_pin(self, digits):
        return digits == self.access_pin


class TwilioController(object):
    def __init__(self, twilio_client, access_manager):
        self.access_manager = access_manager
        self.twilio_client = twilio_client

    def handle_call(self, from_number):
        response = twilio.twiml.Response()
        if from_number in access_manager.door_numbers: # Front Door calling
            response = self.process_call(response)
        else:   # if call is not from the buzzer, then forward the call
            primary_number = self.access_manager.primary_number
            response.dial(primary_number)

        return str(response)
    
    def process_call(self, response):
        perms = self.access_manager.check_permissions()
        if len(perms) > 0:
            response.play(digits='ww999')
            for number in perms.iterkeys():
                message = client.messages.create(to=number, \
                                                # from_=app_number, \
                                                body="Door buzzed")
        elif access_manager.access_pin:
            with response.gather(numDigits=4, action="/handle-pin", method="POST") as g:
                g.say("Enter access codei followed by the hash key")
        else: # if no permissions set, and no access key, then forward the call
            primary_number = self.access_manager.primary_number
            response.dial(primary_number)
        return response

    def process_pin(self, from_number, digits):
        response = twilio.twiml.Response()
        if access_manager.is_valid_pin(digits):
            response.play(digits='ww999')
        else:
            print "Incorrect access code from %s" % from_number
            primary_number = self.access_manager.primary_number
            response.say("Incorrect, please wait")
            response.dial(primary_number)
        return str(response)

    def handle_sms(self, from_number, message):
        response = twilio.twiml.Response()
        result = access_manager.process_instruction(from_number, message)
        response.message(result['reply'])
        return str(response)


app = Flask(__name__)

account_sid = "AC7fdec117c8f2fdf9e1d34d5ef8485b9b"
auth_token = ""
client = TwilioRestClient(account_sid, auth_token)

# app_number = '+16042273188'

access_manager = AccessManager()
access_manager.add_door_number('+16046886429')
access_manager.add_door_number('+17787075262') # debugging purposes
access_manager.add_admin('Phil Jama', '+17787075262', is_primary=True)
access_manager.add_admin('Luc', '+16046498269')

controller = TwilioController(client, access_manager)

@app.route("/doorbuzzer/voice", methods=['GET', 'POST'])
def handle_call():
    from_number = request.values.get('From', None)
    print "Receiving call from %s" % from_number
    return controller.handle_call(from_number)

@app.route("/handle-pin", methods=['GET', 'POST'])
def handle_pin():
    from_number = request.values.get('From', None)
    digits = request.values.get('Digits', None)
    print "Number: %s, Digits: %s" % (from_number, digits)
    return controller.process_pin(from_number, digits)

@app.route("/sms", methods=['GET', 'POST'])
def hello_sms():
    from_number = request.values.get('From', None)
    message_body = request.values.get('Body', None)
    return controller.handle_sms(from_number, message_body)
 
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

