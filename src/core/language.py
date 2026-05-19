from typing import Literal

Lang = Literal["PT", "ES", "EN"]

LANGUAGE_KEYWORDS: dict[str, Lang] = {
    "oi": "PT", "olá": "PT", "ola": "PT", "bom dia": "PT", "boa tarde": "PT",
    "boa noite": "PT", "quero": "PT", "preciso": "PT", "carro": "PT",
    "hola": "ES", "buenos días": "ES", "buenas": "ES", "quiero": "ES",
    "necesito": "ES", "coche": "ES", "auto": "ES",
    "hi": "EN", "hello": "EN", "hey": "EN", "good morning": "EN",
    "good afternoon": "EN", "i want": "EN", "i need": "EN", "car": "EN",
}

MESSAGES: dict[Lang, dict[str, str]] = {
    "PT": {
        "welcome": (
            "Bem-vindo à Sky Motors!\n"
            "Por favor, escolha seu idioma:\n\n"
            "1. Português\n"
            "2. Español\n"
            "3. English"
        ),
        "ask_name": "Pode me dizer seu nome?",
        "ask_interest": (
            "Olá, {name}! Como posso ajudar você hoje?\n\n"
            "1. Comprar um carro\n"
            "2. Vender ou trocar meu carro (trade-in)\n"
            "3. Informações sobre financiamento\n"
            "4. Falar com um vendedor"
        ),
        "ask_vehicle": "Que tipo de veículo você procura? (ex: Honda Civic 2020, SUV, picape...)",
        "ask_budget": "Qual é sua faixa de orçamento? (ex: até $15,000, entre $15k e $25k)",
        "ask_trade_in": "Você tem um veículo para dar como entrada (trade-in)? (sim / não)",
        "ask_trade_in_details": "Me conta sobre o seu veículo: marca, modelo, ano e quilometragem aproximada.",
        "ask_trade_in_payoff": "Esse veículo ainda está financiado? Se sim, qual o saldo devedor aproximado? (sim / não)",
        "ask_financing": "Você vai precisar de financiamento? (sim / não)",
        "ask_down_payment": "Qual é o valor de entrada (down payment) que você tem disponível?",
        "ask_credit_score": (
            "Qual é a sua faixa de crédito aproximada?\n\n"
            "1. Excellent (750+)\n"
            "2. Good (700-749)\n"
            "3. Fair (650-699)\n"
            "4. Building (abaixo de 650)"
        ),
        "ask_pre_approved": "Você já tem pré-aprovação de algum banco ou credit union? (sim / não)",
        "ask_best_time": "Qual o melhor horário para nosso time entrar em contato com você?",
        "ask_trade_vehicle": "Me conta sobre o veículo que você quer vender ou trocar: marca, modelo e ano.",
        "ask_trade_mileage": "Qual é a quilometragem atual do veículo?",
        "ask_trade_condition": (
            "Como você avalia a condição geral do veículo?\n\n"
            "1. Excellent\n2. Good\n3. Fair\n4. Poor"
        ),
        "ask_trade_title": "O veículo tem título limpo (clean title) e você tem o Carfax?",
        "ask_fin_vehicle": "Qual veículo você tem interesse em financiar?",
        "ask_fin_pre_approved": "Você já tem pré-aprovação em algum banco? Se sim, em qual?",
        "agent_redirect": (
            "Sem problema. Vou encaminhar você para um dos nossos consultores agora mesmo. "
            "Por favor, aguarde um instante."
        ),
        "confirm": (
            "Perfeito, {name}. Recebi todas as suas informações.\n\n"
            "Um consultor da Sky Motors vai entrar em contato com você em breve.\n"
            "Obrigado e até logo."
        ),
        "invalid_option": "Por favor, escolha uma das opções disponíveis: 1, 2, 3 ou 4.",
        "invalid_lang": "Não entendi. Por favor, responda com 1, 2 ou 3.",
        "error": "Desculpe, ocorreu um problema técnico. Por favor, tente novamente.",
        "yes_keywords": ["sim", "s", "yes", "y", "sí", "si", "1", "claro", "tenho", "tenho sim", "com certeza", "correto", "certo", "ok", "okay", "exatamente", "isso", "isso mesmo", "quero", "preciso", "tenho sim"],
        "no_keywords": ["não", "nao", "no", "n", "2", "não tenho", "nao tenho", "nunca", "negativo", "de jeito nenhum", "nem pensar", "nope", "nao quero", "não quero"],
    },
    "ES": {
        "welcome": (
            "Bienvenido a Sky Motors!\n"
            "Por favor, elige tu idioma:\n\n"
            "1. Português\n"
            "2. Español\n"
            "3. English"
        ),
        "ask_name": "¿Puedes decirme tu nombre?",
        "ask_interest": (
            "Hola, {name}. ¿En qué te puedo ayudar?\n\n"
            "1. Comprar un carro\n"
            "2. Vender o cambiar mi carro (trade-in)\n"
            "3. Información sobre financiamiento\n"
            "4. Hablar con un asesor"
        ),
        "ask_vehicle": "¿Qué tipo de vehículo buscas? (ej: Honda Civic 2020, SUV, pickup...)",
        "ask_budget": "¿Cuál es tu rango de presupuesto? (ej: hasta $15,000, entre $15k y $25k)",
        "ask_trade_in": "¿Tienes un vehículo para dar como parte de pago (trade-in)? (sí / no)",
        "ask_trade_in_details": "Cuéntame sobre tu vehículo: marca, modelo, año y kilometraje aproximado.",
        "ask_trade_in_payoff": "¿Ese vehículo todavía está financiado? Si es así, ¿cuál es el saldo aproximado? (sí / no)",
        "ask_financing": "¿Vas a necesitar financiamiento? (sí / no)",
        "ask_down_payment": "¿Cuánto tienes disponible para el enganche (down payment)?",
        "ask_credit_score": (
            "¿Cuál es tu rango de crédito aproximado?\n\n"
            "1. Excellent (750+)\n"
            "2. Good (700-749)\n"
            "3. Fair (650-699)\n"
            "4. Building (menos de 650)"
        ),
        "ask_pre_approved": "¿Ya tienes pre-aprobación de algún banco o credit union? (sí / no)",
        "ask_best_time": "¿Cuál es el mejor horario para que nuestro equipo te contacte?",
        "ask_trade_vehicle": "Cuéntame sobre el vehículo que quieres vender o cambiar: marca, modelo y año.",
        "ask_trade_mileage": "¿Cuál es el kilometraje actual del vehículo?",
        "ask_trade_condition": (
            "¿Cómo evalúas la condición general del vehículo?\n\n"
            "1. Excellent\n2. Good\n3. Fair\n4. Poor"
        ),
        "ask_trade_title": "¿El vehículo tiene título limpio (clean title) y tienes el Carfax?",
        "ask_fin_vehicle": "¿Qué vehículo te interesa financiar?",
        "ask_fin_pre_approved": "¿Ya tienes pre-aprobación en algún banco? ¿En cuál?",
        "agent_redirect": (
            "Sin problema. Te voy a conectar con uno de nuestros asesores ahora mismo. "
            "Por favor, espera un momento."
        ),
        "confirm": (
            "Perfecto, {name}. Recibí toda tu información.\n\n"
            "Un asesor de Sky Motors se pondrá en contacto contigo pronto.\n"
            "Gracias y hasta pronto."
        ),
        "invalid_option": "Por favor, elige una de las opciones disponibles: 1, 2, 3 o 4.",
        "invalid_lang": "No entendí. Por favor, responde con 1, 2 o 3.",
        "error": "Lo siento, ocurrió un problema técnico. Por favor, inténtalo de nuevo.",
        "yes_keywords": ["sí", "si", "s", "yes", "y", "1", "claro", "tengo", "por supuesto", "correcto", "exacto", "ok", "okay", "definitivamente", "seguro"],
        "no_keywords": ["no", "n", "2", "no tengo", "nunca", "negativo", "para nada", "nope", "jamás"],
    },
    "EN": {
        "welcome": (
            "Welcome to Sky Motors!\n"
            "Please select your language:\n\n"
            "1. Português\n"
            "2. Español\n"
            "3. English"
        ),
        "ask_name": "What's your name?",
        "ask_interest": (
            "Hi, {name}. How can I help you today?\n\n"
            "1. Buy a car\n"
            "2. Sell or trade in my car\n"
            "3. Financing information\n"
            "4. Talk to a sales consultant"
        ),
        "ask_vehicle": "What type of vehicle are you looking for? (e.g., Honda Civic 2020, SUV, truck...)",
        "ask_budget": "What's your budget range? (e.g., under $15,000, between $15k-$25k)",
        "ask_trade_in": "Do you have a vehicle to trade in? (yes / no)",
        "ask_trade_in_details": "Tell me about your vehicle: make, model, year, and approximate mileage.",
        "ask_trade_in_payoff": "Is that vehicle still financed? If so, what's the approximate payoff amount? (yes / no)",
        "ask_financing": "Will you need financing? (yes / no)",
        "ask_down_payment": "How much do you have available for a down payment?",
        "ask_credit_score": (
            "What's your approximate credit score range?\n\n"
            "1. Excellent (750+)\n"
            "2. Good (700-749)\n"
            "3. Fair (650-699)\n"
            "4. Building (below 650)"
        ),
        "ask_pre_approved": "Have you already been pre-approved by any bank or credit union? (yes / no)",
        "ask_best_time": "What's the best time for our team to reach you?",
        "ask_trade_vehicle": "Tell me about the vehicle you want to sell or trade: make, model, and year.",
        "ask_trade_mileage": "What's the current mileage on the vehicle?",
        "ask_trade_condition": (
            "How would you rate the overall condition of the vehicle?\n\n"
            "1. Excellent\n2. Good\n3. Fair\n4. Poor"
        ),
        "ask_trade_title": "Does the vehicle have a clean title and do you have a Carfax report?",
        "ask_fin_vehicle": "Which vehicle are you interested in financing?",
        "ask_fin_pre_approved": "Have you already been pre-approved at any bank? If so, which one?",
        "agent_redirect": (
            "No problem. I'll connect you with one of our sales consultants right now. "
            "Please hold on for a moment."
        ),
        "confirm": (
            "Perfect, {name}. I've received all your information.\n\n"
            "A Sky Motors consultant will reach out to you shortly.\n"
            "Thank you — talk soon."
        ),
        "invalid_option": "Please choose one of the available options: 1, 2, 3, or 4.",
        "invalid_lang": "I didn't understand that. Please reply with 1, 2, or 3.",
        "error": "Sorry, a technical issue occurred. Please try again.",
        "yes_keywords": ["yes", "y", "1", "sure", "yep", "yeah", "i do", "i have", "of course", "definitely", "absolutely", "correct", "right", "ok", "okay", "affirmative", "certainly", "indeed", "totally"],
        "no_keywords": ["no", "n", "2", "nope", "i don't", "i don't have", "negative", "not really", "nah", "never", "none", "i do not"],
    },
}

CREDIT_SCORE_MAP: dict[str, str] = {
    "1": "Excellent (750+)",
    "2": "Good (700-749)",
    "3": "Fair (650-699)",
    "4": "Building (below 650)",
}

CONDITION_MAP: dict[str, str] = {
    "1": "Excellent",
    "2": "Good",
    "3": "Fair",
    "4": "Poor",
}

INTEREST_MAP: dict[str, dict[Lang, str]] = {
    "1": {"PT": "Comprar um carro", "ES": "Comprar un carro", "EN": "Buy a car"},
    "2": {"PT": "Trade-in / Vender", "ES": "Trade-in / Vender", "EN": "Trade-in / Sell"},
    "3": {"PT": "Financiamento", "ES": "Financiamiento", "EN": "Financing"},
    "4": {"PT": "Falar com vendedor", "ES": "Hablar con vendedor", "EN": "Talk to salesperson"},
}


def detect_language(text: str) -> Lang | None:
    lower = text.lower().strip()
    for keyword, lang in LANGUAGE_KEYWORDS.items():
        if keyword in lower:
            return lang
    return None


def get_message(lang: Lang, key: str, **kwargs: str) -> str:
    msg = MESSAGES[lang].get(key, MESSAGES["EN"].get(key, ""))
    return msg.format(**kwargs) if kwargs else msg


def is_yes(lang: Lang, text: str) -> bool:
    return text.lower().strip() in MESSAGES[lang]["yes_keywords"]


def is_no(lang: Lang, text: str) -> bool:
    return text.lower().strip() in MESSAGES[lang]["no_keywords"]
