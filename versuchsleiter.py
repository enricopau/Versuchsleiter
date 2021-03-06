import logging
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler, AbstractRequestInterceptor
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response
from ask_sdk_core.attributes_manager import AttributesManager, AbstractPersistenceAdapter
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.exceptions import PersistenceException

import msg_data


#Implementiert den Logger zum loggen von Fehlermeldungen, Informationen uvm. 
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
#Instanz des SkillBuilders.
sb = SkillBuilder()
#Die Instanzen der verschiedenen DynamoDbAdapter, die unterschiedliche Daten aus der Datenbank holen und aktualisieren können.
name_adapter = DynamoDbAdapter(table_name="vpn_name", partition_key_name="userId")
aufgaben_adapter = DynamoDbAdapter(table_name="aufgaben_bearbeitet", partition_key_name="userId")
fragen_adapter = DynamoDbAdapter(table_name="antworten_index", partition_key_name="userId")
status_adapter = DynamoDbAdapter(table_name="versuchsleiter_status", partition_key_name="userId")

#Ein Wahrheitswert, der angibt, ob der Nutzer Hilfe benötigt.
looking_for_help = False
#Ein Hilfswert, der angibt, ob der Nutzer direkt zur Befragung/zu den Aufgaben weitergeleitet wird oder erst die Einführungsnachricht zu hören bekommt.
#Hilfswert für den NoIntentHandler
is_no_intent = True

#Wird vor dem Start des Skills ausgeführt und sopeichert den in der Einführung angegeben Namen der VPN und den Skillstatus in den Session Attributen.
class LaunchRequestInterceptor(AbstractRequestInterceptor):
	def process(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		try:
			attrs["name"] = name_adapter.get_attributes(handler_input.request_envelope)
			attrs["aufgaben_index"] = aufgaben_adapter.get_attributes(handler_input.request_envelope)
			attrs["fragen_index"] = fragen_adapter.get_attributes(handler_input.request_envelope)
			attrs["skill_state"] = status_adapter.get_attributes(handler_input.request_envelope)
		except:
			attrs["name"] = "Versuchsperson"
			attrs["aufgaben_index"] = "0"
			attrs["fragen_index"] = "0"
			attrs["skill_state"] = "started"
			name_adapter.save_attributes(handler_input.request_envelope, attrs["name"])
			aufgaben_adapter.save_attributes(handler_input.request_envelope, attrs["aufgaben_index"])
			fragen_adapter.save_attributes(handler_input.request_envelope, attrs["fragen_index"])
			status_adapter.save_attributes(handler_input.request_envelope, attrs["skill_state"])

#Der Handler für den Start des Skills. Hier wird entschieden, auf welchem Stand die "Konversation" ist und dann eine entsprechende Nachricht ausgegeben. Von hier kann der Nutzer die Aufgaben oder die Befragung starten/fortsetzen. 
class LaunchRequesthandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_request_type("LaunchRequest")(handler_input)
	def handle(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		skill_state = attrs["skill_state"]
		name = attrs["name"]
		aufgaben_index = aufgaben_adapter.get_attributes(handler_input.request_envelope)
		fragen_index = fragen_adapter.get_attributes(handler_input.request_envelope)
		intIndex = int(fragen_index)
		noch_fragen = str(10 - intIndex) 

		if skill_state == "started":
			speech = msg_data.versuchsleiter_first_time_msg.format(name)
			if aufgaben_index == "0":
				aufgaben_adapter.save_attributes(handler_input.request_envelope, "1")
			handler_input.response_builder.speak(speech).ask(speech)
		elif skill_state == "aufgaben":
			speech = msg_data.aufgaben_started_msg
			question = msg_data.what_can_i_do_msg
			status_adapter.save_attributes(handler_input.request_envelope, "aufgaben_in_progress")
			if aufgaben_index == "0":
				aufgaben_adapter.save_attributes(handler_input.request_envelope, "1")
			handler_input.response_builder.speak(speech).ask(question)
		elif skill_state == "aufgaben_in_progress":
			speech = msg_data.aufgaben_in_progress_msg.format(name)
			handler_input.response_builder.speak(speech).ask(speech)
		elif skill_state == "fragen":
			speech = msg_data.fragen_started_msg
			question = msg_data.what_can_i_do_msg
			status_adapter.save_attributes(handler_input.request_envelope, "befragung_in_progress")
			if fragen_index == "0":
				fragen_adapter.save_attributes(handler_input.request_envelope, "1")
			handler_input.response_builder.speak(speech).ask(question)
		elif skill_state == "befragung_in_progress":
			speech = msg_data.befragung_in_progress_msg.format(name, noch_fragen)
			question = msg_data.what_can_i_do_msg
			handler_input.response_builder.speak(speech).ask(question)
		elif skill_state == "beendet":
			speech = msg_data.questions_finished_msg
			handler_input.response_builder.speak(speech).set_should_end_session(True)
		else:
			speech = msg_data.error_msg
			logger.info("Es ist Fehler aufgetreten. Der Skillstatus konnte nicht ermittelt werden.")
			handler_input.response_builder.speak(speech).set_should_end_session(True)

		return handler_input.response_builder.response

#Wird aufgerufen wenn die Aufgaben gestartet oder fortgesetzt werden.
class AufgabenStartenIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		skill_state = attrs["skill_state"]
		if skill_state == "started" or skill_state == "aufgaben" or skill_state == "aufgaben_in_progress":
			return is_intent_name("AufgabenStartenIntent")(handler_input) or is_intent_name("AMAZON.YesIntent")(handler_input)
		else:
			return is_intent_name("AufgabenStartenIntent")(handler_input)
	def handle(self, handler_input):
		#attrs = handler_input.attributes_manager.session_attributes
		#name = attrs["name"]
		speech = getTaskSpeech(handler_input)
		handler_input.response_builder.speak(speech)
		return handler_input.response_builder.response

#Wird aufgerufen, wenn die Befragung gestartet oder aufgenommen wird.
class BefragungStartenIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		skill_state = attrs["skill_state"]
		if skill_state == "started" or skill_state == "fragen" or skill_state == "befragung_in_progress":
			return is_intent_name("BefragungStartenIntent")(handler_input) or is_intent_name("AMAZON.YesIntent")(handler_input)
		else:
			return is_intent_name("BefragungStartenIntent")(handler_input)
	def handle(self, handler_input):
		speech = getQuestionSpeech(handler_input)
		handler_input.response_builder.speak(speech).set_should_end_session(False)
		return handler_input.response_builder.response

#Hier war mal ein selbstgeschriebener WiederholenIntentHandler, aber der Built-In Intent funktioniert besser und ohne Komplikation

#Wird aufgerufen, wenn der Nutzer dem Skill mitteilt, dass er fertig ist. Der Handler gibt die nächste Anweisung aus.
class IchBinFertigIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("IchBinFertigIntent")(handler_input)
	def handle(self, handler_input):
		speech = getTaskSpeech(handler_input)
		handler_input.response_builder.speak(speech).set_should_end_session(False)
		return handler_input.response_builder.response

#Wird aufgerufen, wenn der Nutze nach Hilfe fragt.
class HelpIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.HelpIntent")(handler_input)
	def handle(self, handler_input):
		speech = msg_data.help_msg
		question = msg_data.help_question
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response

#Wird aufgerufen wenn in der Befragung eine Antwort gegeben wird.
class AntwortGegebenIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		if attrs["skill_state"] == "befragung_in_progress" or ["skill_state"] == "fragen":
			return is_intent_name("AntwortGegebenIntent")(handler_input)
		else:
			return False
	def handle(self, handler_input):
		fragen_index = fragen_adapter.get_attributes(handler_input.request_envelope)
		fragen_adapter.save_attributes(handler_input.request_envelope, updateIndex(fragen_index))
		speech = getQuestionSpeech(handler_input)
		handler_input.response_builder.speak(speech).set_should_end_session(False)
		return handler_input.response_builder.response

#Wird aufgerufen, wenn der Nutzer die Datenbanken zurücksetzen will.
class DbResetIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("DbResetIntent")(handler_input)
	def handle(self, handler_input):
		index = "0"
		status = "started"
		name = "default"
		try:
			fragen_adapter.save_attributes(handler_input.request_envelope, index)
			aufgaben_adapter.save_attributes(handler_input.request_envelope, index)
			status_adapter.save_attributes(handler_input.request_envelope, status)
			name_adapter.save_attributes(handler_input.request_envelope, name)
			speech = msg_data.reset_successful_msg
		except:
			speech = msg_data.reset_unsuccessful_msg
		handler_input.response_builder.speak(speech).set_should_end_session(True)
		return handler_input.response_builder.response

#Wird aufgerufen, sobald ein Fehler auftritt. Loggt zusätzlich den Fehlergrund
class CatchExceptionsHandler(AbstractExceptionHandler):
	def can_handle(self, handler_input, exception):
		return True
	def handle(self, handler_input, exception):
		speech = msg_data.error_msg
		logger.info("Ein Fehler ist aufgetreten: {}".format(exception))
		handler_input.response_builder.speak(speech).set_should_end_session(True)
		return handler_input.response_builder.response

#Wird aufgerufen, wenn der Nutzer Nein sagt. Soll unterscheiden, ob er dabei eine Frage beantwortet oder in der Anwendug navigiert.
class NoIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		if is_intent_name("AMAZON.NoIntent")(handler_input) and is_no_intent == True:				#is_no_intent Implementation with real question implementation
			return True
		else:
			return False
	def handle(self, handler_input):
		speech = msg_data.no_intent_msg
		question = msg_data.no_intent_question
		handler_input.response_builder.speak(speech).ask(question)
		return handler_input.response_builder.response

#Wird aufgerufen, wenn der Nutzer die Session beenden möchte.
class StopOrCancelIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.StopIntent")(handler_input) or is_intent_name("AMAZON.CancelIntent")(handler_input)
	def handle(self, handler_input):
		attrs = handler_input.attributes_manager.session_attributes
		skill_state = attrs["skill_state"]
		name  = attrs["name"]
		if skill_state == "started" or skill_state == "fragen" or skill_state == "aufgaben":
			speech = msg_data.generic_stop_msg.format(name)
		elif skill_state == "befragung_in_progress":
			speech = msg_data.stop_msg.format(name, "der Befragung")
		elif skill_state == "aufgaben_in_progress":
			speech = msg_data.stop_msg.format(name, "den Aufgaben")
		else:
			speech = msg_data.generic_stop_msg.format(name)
		handler_input.response_builder.speak(speech)
		return handler_input.response_builder.response

#Wird aufgerufen, sobald die Session beendet wird und loggt den Grund für das Beenden. 
class SessionEndedRequestHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_request_type("SessionEndedRequest")(handler_input)
	def handle(self, handler_input):
		logger.info("Session wurde mit folgendem Grund beendet: {}".format(handler_input.request_envelope.request.reason))
		return handler_input.response_builder.response

#Wird aufgerufen, wenn Alexa einen Intent erkennt, dieser aber nicht von diesem Programm abgehandelt werden kann.
class FallbackIntentHandler(AbstractRequestHandler):
	def can_handle(self, handler_input):
		return is_intent_name("AMAZON.FallbackIntent")(handler_input)
	def handle(self, handler_input):
		speech = msg_data.fallback_msg
		handler_input.response_builder.speak(speech)
		return handler_input.response_builder.response

#Funktion, die die richtige Frage ermittelt.
#Funktion, die einen Index um eins erhöht.
def updateIndex(index):
	index = int(index)
	index += 1
	index = str(index)
	return index
#Funktion die die Anweisungen für die richtige Aufgabe wiedergibt.
def getTaskSpeech(handler_input):
	#attrs = handler_input.attributes_manager.session_attributes
	aufgaben_index = aufgaben_adapter.get_attributes(handler_input.request_envelope)
	intIndex = int(aufgaben_index)
	if intIndex == 1:
		speech = msg_data.first_task_msg
		status_adapter.save_attributes(handler_input.request_envelope, "aufgaben_in_progress")
		aufgaben_adapter.save_attributes(handler_input.request_envelope, updateIndex(aufgaben_index))
	elif intIndex == 2:
		speech = msg_data.second_task_msg
		aufgaben_adapter.save_attributes(handler_input.request_envelope, updateIndex(aufgaben_index))
	elif intIndex > 2:
		speech = msg_data.tasks_finished_msg
		status_adapter.save_attributes(handler_input.request_envelope, "fragen")
		if fragen_adapter.get_attributes(handler_input.request_envelope) == "0":
			fragen_adapter.save_attributes(handler_input.request_envelope, "1")
	else:
		speech = msg_data.error_tasks_msg
		logger.info("Ein Fehler ist aufgetreten. Die richtige Aufgabe konnte nicht ermittelt werden.")
	return speech

def getQuestionSpeech(handler_input):
	fragen_index = fragen_adapter.get_attributes(handler_input.request_envelope)
	intIndex = int(fragen_index)
	if intIndex == 1:
		speech = msg_data.first_question
		status_adapter.save_attributes(handler_input.request_envelope, "befragung_in_progress")
	elif intIndex == 2:
		speech = msg_data.second_question
	elif intIndex == 3:
		speech = msg_data.third_question
	elif intIndex == 4:
		speech = msg_data.fourth_question
	elif intIndex == 5:
		speech = msg_data.fifth_question
	elif intIndex == 6:
		speech = msg_data.sixth_question
	elif intIndex == 7:
		speech = msg_data.seventh_question
	elif intIndex == 8:
		speech = msg_data.eight_question
	elif intIndex == 9:
		speech = msg_data.nineth_question
	elif intIndex == 10:
		speech = msg_data.tenth_question
	elif intIndex >= 11:
		speech = msg_data.questions_finished_msg
		status_adapter.save_attributes(handler_input.request_envelope, "beendet")
	else:
		speech = msg_data.error_questions_msg
	return speech




#Adds the Handlers
sb.add_global_request_interceptor(LaunchRequestInterceptor())
sb.add_request_handler(LaunchRequesthandler())
sb.add_request_handler(AufgabenStartenIntentHandler())
sb.add_request_handler(BefragungStartenIntentHandler())
sb.add_request_handler(IchBinFertigIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(AntwortGegebenIntentHandler())
sb.add_request_handler(DbResetIntentHandler())
sb.add_exception_handler(CatchExceptionsHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(StopOrCancelIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())
#Lamda Handler Methode
lambda_handler = sb.lambda_handler()