from enum import Enum

class Modmail:
	class InteractionType(Enum):
		DM = 1
		THREAD = 2

	class Action(Enum):
		CHECK_THREAD_EXISTANCE = 201
		THREAD_DELETE = 202

class ActionPacket(Enum):
	CALLBACK = 1
	HANDOFF = 2

class CreateVoice(Enum):
	MOVE_USER = 101
	USER_PRESENCE = 102

