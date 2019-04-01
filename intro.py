import logging
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler, AbstractRequestInterceptor, AbstractResponseInterceptor
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_model import Response
from ask_sdk_core.attributes_manager import AbstractPersistenceAdapter
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
import msg_data

adapter = DynamoDbAdapter("vpn_name", partition_key_name="userId")


sb = SkillBuilder()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

user_name_slot = "name"


class LaunchRequestHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_request_type("LaunchRequest")(handler_input)

	def handle(self, handler_input):
		speech = "Willkommen. Ich führe dich heute durch die Studie. Bitte gib mir deinen Namen, damit wir weitermachen können."
		question = "Bitte sage etwas wie mein Name ist Max Mustermann."
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response

class FallbackIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.FallbackIntent")(handler_input)
	def handle(self, handler_input):
		speech = msg_data.fallback_msg + "Versuche es mal damit, mir deinen Namen zu nennen."
		question = "Bitte nenne mir deinen Namen um fortzufahren."
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response
class CancelIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.CancelIntent")(handler_input)

	def handle(self, handler_input):
		speech = msg_data.cancel_msg
		question = msg_data.cancel_question_msg
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response
class StopIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.StopIntent")(handler_input)

	def handle(self, handler_input):
		speech = msg_data.goodbye_msg

		handler_input.response_builder.speak(speech).set_should_end_session(True)
		handler_input.response_builder.response
class HelpIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.HelpIntent")(handler_input)
	def handle(self, handler_input):
		speech = "Bitte nenne mir deinen Namen."
		question ="Du kannst mir deinen Namen geben, indem du zum Beispiel etwas sagst wie ich heiße Max Mustermann."
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response
class SessionEndedRequestHandler(AbstractRequestHandler):
 	def can_handle(self, handler_input):
 		return is_request_type("SessionEndedRequest")(handler_input)
 	def handle(self, handler_input):
 		speech = "Auf Wiedersehen."
 		handler_input.response_builder.speak(speech)
 		return handler_input.response_builder.response
class CatchAllExceptionHandler(AbstractExceptionHandler):
	def can_handle(self, handler_input, exception):
		return True

	def handle(self, handler_input, exception):
		print("Encountered following exception: {}".format(exception))

		speech="Entschuldigung, Es ist ein Fehler unterlaufen, bitte versuche es nochmal oder wende dich zur Not an den menschlichen Versuchsleiter!"
		handler_input.response_builder.speak(speech)
		return handler_input.response_builder.response



class MeinNameIstIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("MeinNameIstIntent")(handler_input)

	def handle(self, handler_input):
		slots = handler_input.request_envelope.request.intent.slots
		if user_name_slot in slots:
			user_name = slots[user_name_slot].value
			if user_name == adapter.get_attributes(handler_input.request_envelope):
				speech = "Möchtest du die Einweisung noch einmal hören, {}?".format(user_name)
				handler_input.response_builder.speak(speech).ask(speech)
			else:
				adapter.save_attributes(handler_input.request_envelope, user_name)
				speech = "Schön dich kennenzulernen, {}. In dieser Studie werde ich dich beten, verschiedene, simple Aufgaben zu lösen. Danach werde ich dich beten ein paar Fragen zu beantworten. Deine Teilnahme an dieser Studie ist freiwillig und kann jederzeit ohne die Angabe von Gründen und ohne, dass dir irgendein Nachteil entsteht, beendet werden. Alle erhobenen Daten werden vertraulich behandelt und nicht an Dritte weitergegeben. Wenn du einverstanden und bereit bist loszulegen, starte bitte den Assistenten. ".format(user_name)
				handler_input.response_builder.speak(speech)
		else:
			speech = "Leider kenne ich diesen Namen nicht. Bitte versuche es noch einmal."
			handler_input.response_builder.speak(speech)


		
		return handler_input.response_builder.response

class YesIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.YesIntent")(handler_input)
	def handle(self, handler_input):
		speech = "Willkommen zurück. In dieser Studie werde ich dich beten, verschiedene, simple Aufgaben zu lösen. Danach werde ich dich beten ein paar Fragen zu beantworten. Deine Teilnahme an dieser Studie ist freiwillig und kann jederzeit ohne die Angabe von Gründen und ohne, dass dir irgendein Nachteil entsteht, beendet werden. Alle erhobenen Daten werden vertraulich behandelt und nicht an Dritte weitergegeben. Wenn du einverstanden und bereit bist loszulegen, starte bitte den Assistenten."
		handler_input.response_builder.speak(speech)
		return handler_input.response_builder.response

class NoIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.NoIntent")(handler_input)
	def handle(self, handler_input):
		speech = "Okay. Was kann ich dann für dich tun?"
		question = "Also, was kann ich für dich tun?"
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response


sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(CancelIntentHandler())
sb.add_request_handler(StopIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())
sb.add_request_handler(MeinNameIstIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())

lambda_handler = sb.lambda_handler()
