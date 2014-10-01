from flask import Flask, request, redirect
from copy import deepcopy
import twilio.twiml
from twilio.rest import TwilioRestClient
import datetime
import pytz
import re

app = Flask(__name__)

account_sid = "AC7fdec117c8f2fdf9e1d34d5ef8485b9b"
auth_token = "a865179db0d5cf7371063be27f207616"
client = TwilioRestClient(account_sid, auth_token)

app_number = '+17787650226'
front_door = ['+16046840467', '+17787075262']
access_code = '1234'

numbers = {
  'Phil Jama': '+17787075262',
  'Eric Fardy': '+17788774570',
  'Ray Horan': '+16043537081',
  'Mason Lampard': '+16048038331',
}
permissions = {}#'+17787075262': datetime.datetime.now() + datetime.timedelta(seconds=120)} 

def check_permissions():
    tmp_permissions = deepcopy(permissions)
    time_now = datetime.datetime.now()
    for number, expiry in tmp_permissions.iteritems():
        if time_now > expiry:
            print "Deleting expired permission"
            permissions.pop(number)
    return permissions


@app.route("/doorbuzzer/voice", methods=['GET', 'POST'])
def handle_call():
    from_number = request.values.get('From', None)
    resp = twilio.twiml.Response()

    if from_number in front_door: # Front Door calling
        perms = check_permissions()
        print "Permissions: %s" % perms
        if len(perms) > 0:
            resp.play(digits='www666')
            for number in permissions.iterkeys():
                message = client.messages.create(to=number, from_=app_number, body="Door buzzed")
        elif access_code:
            with resp.gather(numDigits=4, action="/handle-key", method="POST") as g:
                g.say("Enter access code")
        else:
            resp.dial(numbers['Phil Jama'])
    else:
        resp.dial(numbers['Phil Jama'])

    return str(resp)


@app.route("/handle-key", methods=['GET', 'POST'])
def handle_key():
    digits = request.values.get('Digits', None)
    print "Digits: %s" % digits
    resp = twilio.twiml.Response()
    if digits == access_code:
        resp.play(digits='www666')
        return str(resp)
    else:
        resp.say("Incorrect. Goodbye")
        return str(resp)


def get_expiry(secs):
   return datetime.datetime.now() + datetime.timedelta(seconds=secs)

def format_dt(dt):
    dt = dt.replace(tzinfo=pytz.timezone('UTC'))
    tz = pytz.timezone('US/Pacific')
    return dt.astimezone(tz).strftime("%H:%M:%S %Z")

def authorize(number, expiry):
    print "Adding permissions: %s" % (format_dt(expiry))
    permissions[number] = expiry

    resp = twilio.twiml.Response()
    date_str = format_dt(expiry)
    return date_str
    
def clear_permissions():
    print "Clearing all permissions"
    permissions = {}

@app.route("/sms", methods=['GET', 'POST'])
def hello_sms():
    from_number = request.values.get('From', None)
    resp = twilio.twiml.Response()
    if from_number in numbers.values():
        message = request.values.get('Body', None)
        print "Message: '%s', Type: %s" % (message, type(message))
        if isinstance(message, unicode) and message.isnumeric():
            expiry = get_expiry(int(message) * 60)
            date_str = authorize(from_number, expiry)
            resp.message("Confirmed. Valid till %s" % date_str)
            return str(resp)
        elif message.lower().startswith('open for '):
            matches = re.findall('\b*\d+$', message)
            if matches and len(matches) > 0 and matches[-1] >= 0:
                expiry = get_expiry(int(matches[-1]) * 60)
                date_str = authorize(from_number, expiry)
                resp.message("Confirmed. Valid till %s" % date_str)
                return str(resp)
        elif message.lower() == "clear":
            clear_permissions()
            resp.message("Permissions Cleared.")
            return str(resp)

    resp.message("Error")
    return str(resp)
 
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

