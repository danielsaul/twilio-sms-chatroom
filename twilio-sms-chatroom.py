import os
from flask import Flask
from flask import request
from twilio.rest import TwilioRestClient
from twilio import twiml

app = Flask(__name__)
client = TwilioRestClient()
twilio_number = "+442071838653"

participants = {}

@app.route('/')
def index():
    return "SMS Chatroom"

# Received an SMS
@app.route('/sms', methods=['GET','POST'])
def sms():

    # Check its a POST request
    if request.method != 'POST':
        print "---> Received invalid sms request: method wasn't POST"
        return "Request method must be POST."
    
    from_number = request.form['From']
    print from_number
    if not from_number.startswith("+"):
        print "---> Received SMS from invalid phone number"
        return ''
    message = request.form['Body']
    if not message:
        print "---> Received blank sms from %s" % (from_number)
        return ''

    if message.startswith("#"):
        #Command
        sms_command(from_number, message)
        return ''

    if from_number in participants:
        # Existing Number
        sms_received_msg(from_number, message)
    else:
        # New Number and not a Command
        sendmsg(from_number, "You must first join the chat using the command '#JOIN <username>'")
        print "---> Received message from unknown number, %s"

    return ''

# Command
def sms_command(from_number, message):
    command = string.split(message, " ", 1)
    command(from_number, message)
    return


# Send an SMS to a number via twilio
def sendmsg(num, msg):
    message = client.sms.messages.create(to=num, body=msg, from_=config('TWILIO_PHONE_NUMBER'))


def config(var):
    try:
        return os.environ[var]
    except KeyError:
        print "Could not find {0} in env, quitting.".format(var)
        sys.exit(1)

# Start flask
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
