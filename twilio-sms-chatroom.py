import os
import string
import redis
from flask import Flask
from flask import request
from twilio.rest import TwilioRestClient


flask_app = Flask(__name__)
twilio_client = TwilioRestClient()
r = redis.StrictRedis(host='localhost', port=6379, db=0)
running = True

@flask_app.route('/')
def index():
    return "SMS Chatroom"

# Received an SMS
@flask_app.route('/sms', methods=['GET','POST'])
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

    if message.lower().startswith("#start") or message.lower().startswith("#stop") or message.lower().startswith("#close") :
        #Admin command
        sms_command(from_number, message)
        return 'Received command'
    
    if not running: return 'Not running'

    if message.startswith("#"):
        #Command
        sms_command(from_number, message)
        return 'Received command'

    if r.sismember("participants", from_number):
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
    if len(command) == 1:
        command.append('')
    participant = r.sismember("participants", from_number)
    try:
        globals()[command[0].lower()[1:]](from_number, participant, command[1])
    except:
        print "---> Invalid command received from %s (%s)" % (from_number, command[0])
        sendmsg(from_number, ">> Invalid command.")

# Close the Chatroom
def close_chat():
    msgall(">> Chatroom closing.")
    running = False
    for x in r.smembers("participants"):
        leave(x, True)
    running = True

# Get a phone number from a nickname
def get_number(nickname):
    for x in r.smembers("participants"):
        if r.get("participant:%s:nickname" % x) = nickname:
            return x
    return False

# Send a message to all participants (excl. 2nd arg)
def msgall(message, exclude=0):
    print message
    for x in r.smembers("participants"):
        if x != exclude:
            sendmsg(x, message)
    return

# Received message to relay to other participants
def smsreceivedmsg(number, message):
    nickname = r.get("participant:%s:nickname" % number)
    if len(message) > 120:
        print "---> Message from %s is too long." % nickname
        sendmsg(number, ">> Messages must not be longer than 120 characters")
        return
    finalmsg = "<%s> %s" % (nickname, message)
    msgall(finalmsg, number)

# Send an SMS to a number via twilio
def sendmsg(num, msg):
    if running:
        try:
            message = twilio_client.sms.messages.create(to=num, body=msg, from_=config('TWILIO_PHONE_NUMBER'))
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
    flask_app.run(host='0.0.0.0', port=port)







#######################################
### COMMANDS ##########################
#######################################

# Someone wants to join
def join(from_number, participant, nickname):
    if len(nickname) > 15 or len(nickname) < 3:
        print "---> Nickname for joinee, %s, is too long or too short." % from_number
        sendmsg(from_number, ">> Nickname must be between 3 and 20 characters")
        return
    if r.sismember("banned", from_number):
        print "---> Banned user, %s, tried to join." % from_number
        return

    if r.sadd("participants", from_number):
        if r.sadd("nicknames", nickname):
            r.set("participant:%s:nickname" % (from_number), nickname)
            sendmsg(from_number, ">> Welcome to the chat, %s. Currently %s users." % (nickname, r.scard("participants")))
            if r.scard("participants") = 1:
                # First participant becomes admin
                r.sadd("admins", from_number)
                sendmsg(from_number, ">> You are the admin for this chat.")
            msgall(">> %s has joined the chat." % (nickname), from_number)
        else:
            print "---> Nickname for joinee, %s, is already in use." % from_number
            sendmsg(from_number, ">> Nickname already in use.")
            r.srem("participants", from_number)
    else:
        print "---> %s has already joined." % from_number

# Someone wants to leave
def leave(from_number, participant, msg=''):
    if participant:
        nickname = r.get("participant:%s:nickname" % from_number)
        if msg != '':
            msgall(">> %s %s" % nickname, msg)
        else:
            msgall( ">> %s has left the chat." % nickname)
        r.srem("participants", from_number)
        r.srem("nicknames", nickname)
        r.delete("participant:%s:nickname" % from_number)

        if r.srem("admins", from_number) and r.scard("admins") = 0:
            # No admins left, chat closes
            close_chat()

# Someone wants to change their nickname
def nick(from_number, participant, new):
    current = r.get("participant:%s:nickname" % from_number)
    
    if not participant: return

    if len(new) > 15 or len(new) < 3:
        print "---> New nickname for %s is too long or too short." % current
        sendmsg(from_number, ">> Nickname must be between 3 and 20 characters")
        return

    if r.sadd("nicknames", new):
        r.srem("nicknames", current)
        r.set("participant:%s:nickname" % (from_number), new)
        msgall(">> %s is now known as %s" % (current, new))
    else:
        print "---> New nickname for %s is already in use." % current
        sendmsg(from_number, ">> Nickname already in use.")
        return

# Someone wants a list of participants
def names(from_number, participant, msg=''):
    if not participant: return

    finalmsg = ">> Currently %s users." % r.scard("nicknames")
    for x in r.smembers("nicknames"):
        finalmsg += "  %s" % (x)
    print finalmsg
    sendmsg(from_number, finalmsg)

# An admin wants to make someone else an admin
def admin(from_number, participant, adminee):
    if r.sismember("admins", from_number) and r.sismember("nicknames", adminee):
        number = get_number(adminee)
        r.sadd("admins", number)
        msgall(">> %s has been elevated to an admin." % adminee)

# An admin wants to kick someone
def kick(from_number, participant, kickee):
    if r.sismember("admins", from_number) and r.sismember("nicknames", kickee):
        leave(get_number(kickee), True, "has been kicked from the chat.")

# An admin wants to ban someone
def ban(from_number, participant, banee):
    if r.sismember("admins", from_number) and r.sismember("nicknames", banee):
        number = get_number(banee)
        leave(number, True, "has been banned from the chat.")
        r.sadd("banned", number)

def start(from_number, participant, msg=''):
    if r.sismember("admins", from_number):
        running = True
        msgall(">> Chat resumed.")

def stop(from_number, participant, msg=''):
    if r.sismember("admins", from_number):
        msgall(">> Chat is being temporarily paused.")
        running = False

def close(from_number, participant, msg=''):
    if r.sismember("admins", from_number):
        close_chat()

####################################################
####################################################
