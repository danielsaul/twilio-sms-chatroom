import os
import string
from flask import Flask
from flask import request
from twilio.rest import TwilioRestClient
from twilio import twiml

app = Flask(__name__)
client = TwilioRestClient()

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
    if not from_number.startswith("+"):
        print "---> Received SMS from invalid phone number"
        return 'Invalid number'
    message = request.form['Body']
    if not message:
        print "---> Received blank sms from %s" % (from_number)
        return 'Blank message'

    if message.startswith("#"):
        #Command
        sms_command(from_number, message)
        return 'Received command'

    if from_number in participants:
        # Existing Number
        smsreceivedmsg(from_number, message)
    else:
        # New Number and not a Command
        print "---> Received message from unknown number, %s" % (from_number)
        sendmsg(from_number, ">> You must first join the chat using the command '#JOIN <nickname>'")

    return 'Done'

# Command
def sms_command(from_number, message):
    command = message.split(" ", 1)
    try:
        globals()[command[0].lower()[1:]](from_number, command[1])
    except:
        print "---> Invalid command received from %s (%s)" % (from_number, command[0])
        sendmsg(from_number, ">> Invalid command.")

# Someone wants to join
def join(from_number, username):
    if from_number in participants:
        print "---> %s has already joined." % (from_number)
        return
    if len(username) > 15 or len(username) < 3:
        print "---> Nickname for joinee, %s, is too long or too short." % (from_number)
        sendmsg(from_number, ">> Nickname must be between 3 and 20 characters")
        return
    if username in participants.values():
        print "---> Nickname for joinee, %s, is already in use." % (from_number)
        sendmsg(from_number, ">> Nickname already in use.")
        return
    participants[from_number] = username
    print ">> %s has joined the chat." % (username)
    sendmsg(from_number, ">> Welcome to the chat, %s" % (username))
    msgall(">> %s has joined the chat." % (username), from_number) 

# Someone wants to leave
def leave(from_number, msg):
    if from_number in participants:
        print ">> %s has left the chat." % (participants[from_number])
        msgall( ">> %s has left the chat." % (participants[from_number]))
        del participants[from_number]
    else:
        print "---> %s tried to leave without having ever joined." % (from_number)

# Someone wants to change their nickname
def nick(from_number, new):
    if from_number not in participants:
        print "---> %s tried to change nickname without having ever joined." % (from_number)
        sendmsg(from_number, ">> You must first join the chat using '#JOIN <nickname>' before using that command."
        return
    if len(new) > 15 or len(new) < 3:
        print "---> New nickname for %s is too long or too short." % (participants[from_number])
        sendmsg(from_number, ">> Nickname must be between 3 and 20 characters")
        return
    if new in participants.values():
        print "---> New nickname for %s is already in use." % (participants[from_number])
        sendmsg(from_number, ">> Nickname already in use.")
        return
    print ">> %s is now known as %s." % (participants[from_number],new)
    msgall(">> %s is now known as %s." % (participants[from_number],new)) 
    participants[from_number] = new

# Send a message to all participants (excl. 2nd arg)
def msgall(message, exclude=0):
    for x in participants:
        if x != exclude:
            sendmsg(x, message)
    return

# Received message to relay to other participants
def smsreceivedmsg(number, message):
    if len(message) > 120:
        print "---> Message from %s is too long." % (participants[number])
        sendmsg(number, ">> Messages must not be longer than 120 characters")
        return
    finalmsg = "<%s> %s" % (participants[number], message)
    print finalmsg
    msgall(finalmsg, number)

# Send an SMS to a number via twilio
def sendmsg(num, msg):
    try:
        message = client.sms.messages.create(to=num, body=msg, from_=config('TWILIO_PHONE_NUMBER'))
    except:
        print "---> Error sending SMS to %s" % (num)


def config(var):
    try:
        return os.environ[var]
    except KeyError:
        print "Could not find {0} in env, quitting.".format(var)
        sys.exit(1)

# Start flask
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

