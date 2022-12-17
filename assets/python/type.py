class Modmail:
	class InteractionType:
		DM = 1
		THREAD = 2

	class Action:
		CHECK_THREAD_EXISTANCE = 201
		THREAD_DELETE = 202

class ActionPacket:
	CALLBACK = 1
	HANDOFF = 2

class CreateVoice:
	CREATE_CHANNEL = 101

