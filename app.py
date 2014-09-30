from flask import Flask, request, redirect
import twilio.twiml
import datetime

app = Flask(__name__)

front_door = '+17787075262'

numbers = {
  'Phil Jama': '+17787075262',
  'Eric Fardy': '+17788774570',
  'Ray Horan': '+16043537081',
}
 
@app.route("/", methods=['GET', 'POST'])
def hello_monkey():
    from_number = request.values.get('From', None)
    if from_number in numbers:
        caller = numbers[from_number]
    else:
        caller = "Monkey"

    resp = twilio.twiml.Response()
    # Greet the caller by name
    resp.say("Hello " + caller)
 
    with resp.gather(numDigits=1, action="/handle-key", method="POST") as g:
        g.say("To speak to a real monkey, press 1. Press any other key to start over.")

    return str(resp)

@app.route("/doorbuzzer/voice", methods=['GET', 'POST'])
def handle_call():
  from_number = request.values.get('From', None)
  resp = twilio.twiml.Response()

  if from_number == front_door:
    resp.play(digits='www555')
  else:
    resp.dial(numbers['Eric Fardy'])

  return str(resp)


@app.route("/sms", methods=['GET', 'POST'])
def hello_sms():
    resp = twilio.twiml.Response()
    resp.message("Hello, Mobile Monkey")
    return str(resp)

 
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

