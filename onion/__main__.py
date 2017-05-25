# Test file for development

from onion import Onion

onion = Onion("irc.freenode.net", 6697, 3, use_ssl=True)

@onion.ring("setup")
def setup(cli, num):
    cli.send("NICK", "TestBot" + str(num), target=num)
    cli.send("USER", "TestBot", "irc.freenode.net", "irc.freenode.net", ":This is a test bot", target=num)

@onion.ring("PING")
def on_ping(cli, num, prefix, server):
    cli.send("PONG", server, target=num)

@onion.ring("PRIVMSG")
def on_privmsg(cli, num, sender, target, message):
    if message == "!!" and num == 0:
        cli.send("PRIVMSG", target, ":I AM ALIVE!!")

@onion.ring("endofmotd")
def endofmotd(cli, num, prefix, *args):
    cli.send("JOIN", "#lykos-test", target=num)

onion.run()
