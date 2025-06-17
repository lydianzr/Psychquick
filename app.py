# app.py - Flask Backend for PsychQuick (State Machine Conversation Flow Corrected)


from flask import Flask, request, jsonify, render_template, session
import os # For SECRET_KEY
import re # For more robust keyword matching
import time # For simulating processing delay
import random # For random acknowledgments


# Initialize Flask app# app.py - Flask Backend for PsychQuick (State Machine Conversation Flow Corrected)


from flask import Flask, request, jsonify, render_template, session
import os # For SECRET_KEY
import re # For more robust keyword matching
import time # For simulating processing delay
import random # For random acknowledgments


# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
# A secret key is REQUIRED for Flask sessions to work.
# In a real application, this should be a strong, randomly generated key stored securely (e.g., environment variable).
app.secret_key = os.urandom(24)


# --- Configuration and Data ---


# Keywords and their scores for different symptom categories
# Increased score values to make symptoms more impactful for triggering follow-ups
SYMPTOM_KEYWORDS = {
    'depression': {
        r'\bsad\b': 5, r'\bdown\b': 5, r'\bhopeless\b': 5, r'\bdepressed\b': 5,
        r'\btired\b': 3, r'\bfatigue\b': 3, r'\blow energy\b': 3,
        r'\blost interest\b': 5, r'\bno pleasure\b': 5, r'\banhedonia\b': 5,
        r'\bworthless\b': 4, r'\bguilty\b': 4, r'\bcrying\b': 3, r'\bempty\b': 3,
        r'\bappetite change\b': 2, r'\bweight change\b': 2, r'\cry\b': 3,
        r'\bdifficulty concentrating\b': 2, r'\bmind is blank\b': 2,
        r'\bno motivation\b': 3, r'\bfeeling numb\b': 3,
    },
    'anxiety': {
        r'\bworry\b': 5, r'\banxious\b': 5, r'\bnervous\b': 5, r'\brestless\b': 5,
        r'\bpanic\b': 5, r'\bfear\b': 5, r'\bdread\b': 5,
        r'\bheart racing\b': 4, r'\bshortness of breath\b': 4, r'\bsweating\b': 3,
        r'\birritable\b': 3, r'\bon edge\b': 3, r'\bconstant worry\b': 5,
        r'\bavoiding\b': 2, r'\bshaking\b': 3, r'\btrembling\b': 3,
        r'\bunease\b': 3, r'\bchest pain\b': 3, r'\bnausea\b': 2,
    },
    'stress': {
        r'\bstressed\b': 5, r'\boverwhelmed\b': 5, r'\btense\b': 5, r'\bburnout\b': 5,
        r'\bdifficulty relaxing\b': 3, r'\bcan\'t switch off\b': 3,
        r'\bfrustrated\b': 3, r'\bimpatient\b': 3,
        r'\bheadache\b': 2, r'\bmuscle tension\b': 2,
        r'\bpressure\b': 3, r'\bdemands\b': 3, r'\bexhausted\b': 3, r'\bfeeling drained\b': 3,
    },
    'sleep': { # Reflects SSS (Sleep Symptom Scale) concepts
        r'\binsomnia\b': 5, r'\bdifficulty sleeping\b': 5, r'\bcan\'t fall asleep\b': 5,
        r'\bwaking up early\b': 4, r'\bwaking often\b': 4, r'\btrouble sleeping\b': 5,
        r'\bnot refreshed\b': 4, r'\bpoor quality sleep\b': 4, r'\bsleep problems\b': 5,
        r'\bdaytime sleepiness\b': 3, r'\bsleeping too much\b': 3, r'\bsleep deprived\b': 4,
    },
    'perceived_stress': { # Reflects PSS (Perceived Stress Scale) concepts
        r'\bunable to cope\b': 5, r'\bthings are out of control\b': 5, r'\bcan\'t handle\b': 5,
        r'\bdifficulties piling up\b': 4, r'\bnervous about demands\b': 4, r'\boverload\b': 4,
        r'\bfeeling helpless\b': 4,
    },
    'suicidal_thoughts': {
        r'\bsuicidal\b': 20, r'\bend it all\b': 20, r'\bharm myself\b': 20, r'\bkill myself\b': 20,
        r'\bwant to die\b': 20, r'\bnot want to live\b': 20, r'\bself-harm\b': 20,
    },
    'medical_condition': {
        r'\bmedical condition\b': 10, r'\bmedication\b': 10, r'\bdiabetes\b': 10, r'\bheart disease\b': 10,
        r'\bthyroid\b': 10, r'\bchronic illness\b': 10, r'\bphysical illness\b': 10,
        r'\bpre-existing condition\b': 10, r'\btaking pills\b': 10, r'\bhealth issue\b': 10,
    }
}


# Severity thresholds
SEVERITY_THRESHOLDS = {
    'Extremely Severe': 25, # Adjusted thresholds for new scoring
    'Severe': 15,
    'Moderate': 8,
    'Mild': 3,
    'Minimal': 0,
}


# Malaysia-specific hotlines and resources
MALAYSIA_RESOURCES = {
    'hotlines': [
        {"name": "Befrienders Kuala Lumpur", "number": "03-7956 8145", "hours": "24 hours", "website": "https://www.befrienders.org.my/"},
        {"name": "Befrienders Penang", "number": "04-281 5161", "hours": "3pm - midnight", "website": "https://www.befrienders.org.my/centre-in-malaysia"},
        {"name": "Befrienders Ipoh", "number": "05-547 7933", "hours": "4pm - 11pm", "website": "https://www.befrienders.org.my/centre-in-malaysia"},
        {"name": "Malaysian Mental Health Association (MMHA)", "number": "03-2780 6803", "hours": "Mon-Fri, 10am-5pm", "website": "https://mmha.org.my/"},
        {"name": "Talian Kasih", "number": "15999 or WhatsApp +60192615999", "hours": "24 hours", "website": "https://www.kpwkm.gov.my/"},
        {"name": "MIASA Crisis Helpline", "number": "1-800-180-066", "hours": "24/7", "website": "https://www.miasa.org.my/"},
        {"name": "RELATE Malaysia (online psychotherapy)", "website": "https://relate.com.my/"},
        {"name": "SOLS Health", "number": "6018-664-0247", "website": "https://www.sols247.org/solshealth"},
        {"name": "Life Line Association Malaysia", "number": "03-42657995", "website": "http://lifeline.org.my/cn/"},
        {"name": "Women's Aid Organization (WAO)", "number": "+603 7956 3488", "whatsapp": "+6018 988 8058", "website": "https://wao.org.my/"},
    ],
    'therapist_guidance': [
        "You can find qualified therapists through the Ministry of Health's search portal: https://mhps.moh.gov.my/SEARCH/",
        "The Malaysian Society of Clinical Psychology (MSCP) also maintains a directory: https://www.mscp.my/clinical-psychologist-registry",
        "The Malaysian Mental Health Association (MMHA) provides psychological therapy services, sometimes with financial subsidies: https://mmha.org.my/find-help",
        "Consider governmental health clinics (Klinik Kesihatan) for referrals to public hospital psychiatric departments, which are often more affordable.",
        "Online platforms like ThoughtFull.world also list therapists in Malaysia: https://www.thoughtfull.world/professionals/therapy-near-me-malaysia",
        "TherapyRoute.com also lists psychologists, counsellors, & therapists in Malaysia: https://www.therapyroute.com/therapists/malaysia/1",
    ]
}


# Define conversational stages and follow-up questions
# Significantly expanded and refined questions for more in-depth conversation
CONVERSATIONAL_FLOW = {
    'general_prompt': "Please describe any symptoms you are experiencing. For example, 'I feel sad and tired all the time.' or 'I worry a lot about the future.'",
    'initial_medical_check_question': "Do you have any pre-existing medical conditions or are you currently taking any medications? (This helps me provide safer recommendations.)",
    'depression_followup': [
        "On a scale of 0 to 3 (0=Did not apply to me at all, 1=Applied to me to some degree, or some of the time, 2=Applied to me to a considerable degree, or a good part of time, 3=Applied to me very much, or most of the time): How much did you feel that you couldn't seem to experience any positive feeling at all?", # DASS-like
        "How often have you found it difficult to get started on things you needed to do?", # DASS-like
        "Have you felt that life was meaningless or that you had nothing to look forward to?", # DASS-like
        "How frequently have you felt down-hearted and blue?", # DASS-like
        "Have you experienced any changes in your interest in activities you once enjoyed?", # DASS-like, broader
        "On a scale of 1 to 10, how would you rate your overall mood on most days (1 being very low, 10 being very high)?",
        "How has your ability to feel pleasure or joy been lately? Is it difficult to find enjoyment in things?",
        "Have you noticed changes in your sleep patterns (e.g., sleeping too much, too little, difficulty staying asleep)?",
        "How has your appetite been, and have you experienced any significant weight changes without trying?",
        "Do you often feel restless or slowed down in your movements or speech, so much that others have noticed?",
        "How frequently do you have thoughts that you are a failure or that you have let yourself or your family down?",
        "Have you had recurrent thoughts of death, or any thoughts of harming yourself? (Please answer honestly, your safety is paramount.)", # Suicidal ideation question (Index 11)
        "If you answered 'yes' to the previous question, have you taken any steps or made any preparations toward those thoughts?", # Critical follow-up (Index 12)
        "Can you describe a typical day for you recently, focusing on your energy levels and mood throughout the day?",
        "What kind of thoughts typically run through your mind when you're feeling sad or down?",
        "Have you found yourself isolating from others, or avoiding social interactions more than usual?",
        "Is there a particular time of day when your mood tends to be at its lowest?",
        "What activities, if any, still bring you a sense of relief or small moments of happiness?",
        "How has your concentration or ability to focus on tasks been affected?",
        "Do you find yourself dwelling on past events, or feeling excessive guilt or remorse?",
        "Are there any specific situations or events that seem to trigger or worsen your low mood?",
        "How would you describe your self-esteem and self-worth lately?",
    ],
    'anxiety_followup': [
        "On a scale of 0 to 3: How much did you feel you were close to panic?", # DASS-like
        "How often have you been aware of dryness of your mouth, or difficulty breathing?", # DASS-like physical symptoms
        "Have you experienced any sudden feelings of intense fear, terror, or apprehension, sometimes with a racing heart, sweating, or dizziness?", # Panic attack type questions
        "How often do you find yourself worrying excessively about a variety of things, even small daily issues?",
        "Do you often feel keyed up, on edge, or restless?",
        "How much difficulty do you have relaxing or calming down?",
        "Do you find yourself avoiding certain situations, places, or activities because you anticipate feeling anxious or having a panic attack?",
        "How often do you experience a racing heart, trembling, or shortness of breath when you're feeling anxious?",
        "Has your anxiety caused you significant distress or impairment in social, occupational, or other important areas of functioning?",
        "How long have you been experiencing these anxious feelings, and are they present most days?",
        "Can you describe a recent situation where you felt particularly anxious? What happened?",
        "What kind of thoughts typically accompany your anxious feelings?",
        "Do you experience physical symptoms like muscle tension, headaches, or stomach issues when you're anxious?",
        "How much do you worry about future events, even those that are unlikely to happen?",
        "Do you find it hard to control your worrying once it starts?",
        "Have you had any experiences where you felt a sudden, overwhelming surge of intense fear or discomfort, often called a 'panic attack'?",
        "Do you ever feel a sense of impending doom or danger without a clear reason?",
        "How does your anxiety affect your ability to sleep or eat?",
        "What strategies do you currently use to try and manage your anxiety?",
        "Do you ever feel detached from your body or your surroundings when you're anxious?",
    ],
    'stress_followup': [
        "On a scale of 0 to 3: How much did you tend to over-react to situations?", # DASS-like
        "How often have you found it hard to wind down after a busy day?", # DASS-like
        "How much did you feel that you were rather touchy or easily irritated?", # DASS-like
        "Do you often feel that you are unable to control the important things in your life, or that difficulties are piling up?", # PSS-like
        "How often have you felt nervous and 'stressed out' because of demands on your time or energy?", # PSS-like
        "How often do you feel overwhelmed by your responsibilities?",
        "Have you noticed physical symptoms like chronic headaches, muscle tension, or digestive issues that you link to stress?",
        "How has your stress affected your relationships, work performance, or academic progress?",
        "What are the main sources of stress in your life right now? Can you list a few?",
        "What coping strategies do you typically use when you feel stressed, and how effective are they?",
        "How often do you feel that you cannot cope with all the things that you have to do?",
        "Do you feel that you are on top of things, or often feel overwhelmed?",
        "How effectively have you been able to control irritations in your life?",
        "How often have you felt that things were going your way recently?",
        "Do you find yourself procrastinating more when you're stressed?",
        "How does stress impact your decision-making abilities?",
        "Have you noticed changes in your appetite or eating habits due to stress?",
        "Do you feel more physically fatigued when you're under stress?",
        "How do you typically wind down or relax after a stressful period?",
        "Are there any specific situations or people that consistently trigger your stress?",
    ],
    'sleep_followup': [
        "On a scale of 0 to 3: How much did you find it difficult to fall asleep?", # SSS-like
        "How often do you wake up earlier than desired, or wake up frequently during the night?", # SSS-like
        "Do you feel unrefreshed or tired even after what seems like a full night's sleep?", # SSS-like
        "On average, how many hours of sleep do you get per night?",
        "How would you rate the overall quality of your sleep (e.g., restless, deep, interrupted)?",
        "Has your sleep problem been ongoing for more than a month? If so, for how long?",
        "Does your sleep issue significantly impact your daytime functioning, energy levels, or mood?",
        "Are there specific thoughts or worries that keep you awake at night?",
        "Do you have a consistent bedtime and wake-up time, even on weekends?",
        "What strategies have you already tried to improve your sleep, and what were the results?",
        "How long does it typically take you to fall asleep once you get into bed?",
        "Do you often wake up feeling tired even after a full night's sleep?",
        "How frequently do you wake up during the night and have difficulty falling back asleep?",
        "Do you experience restless legs or any other physical discomfort that interferes with your sleep?",
        "How often do you feel drowsy or fall asleep unintentionally during the day (e.g., while watching TV, reading, or driving)?",
        "What does your bedtime routine typically look like? (e.g., screen time, food/drink, activities)",
        "Is your sleep environment dark, quiet, and cool?",
        "Do you consume caffeine or alcohol, especially in the hours leading up to bedtime?",
        "Have you ever been told you snore loudly or stop breathing during sleep?",
        "How has your sleep problem affected your ability to concentrate, your memory, or your overall performance?",
    ],
    'perceived_stress_followup': [
        "On a scale of 0 to 4 (0=Never, 1=Almost Never, 2=Sometimes, 3=Fairly Often, 4=Very Often): How often have you been upset because of something that happened unexpectedly?", # PSS question
        "How often have you felt that you were unable to control the important things in your life?", # PSS question
        "How often have you felt nervous and 'stressed'?", # PSS question
        "How often have you dealt successfully with irritating life hassles?", # PSS question, reversed score potential
        "How often have you felt that you were effectively coping with important changes that were occurring in your life?", # PSS question, reversed score potential
        "How often have you felt confident about your ability to handle your personal problems?", # PSS question, reversed score potential
        "How often have you felt that things were going your way?", # PSS question, reversed score potential
        "How often have you found that you could not cope with all the things that you had to do?", # PSS question
        "How often have you been able to control irritations in your life?", # PSS question, reversed score potential
        "How often have you felt that you were on top of things?", # PSS question, reversed score potential
        "How often do you feel that personal difficulties are piling up so high that you cannot overcome them?",
        "In the last month, how often have you felt that you were unable to control the important things in your life?",
        "How often in the last month have you felt confident about your ability to handle your personal problems?",
        "How often in the last month have you felt that difficulties were piling up so high that you could not overcome them?",
        "How often in the last month have you felt that you were unable to cope with all the things that you had to do?",
        "How often in the last month have you felt that you were on top of things?",
        "How often in the last month have you been angered because of things that happened that were out of your control?",
        "How often in the last month have you felt that you were dealing effectively with the changes in your life?",
        "How often in the last month have you found yourself thinking about things that you have to accomplish?",
        "How often in the last month have you felt that you were able to control irritations in your life?",
    ],
    'medical_condition_followup': [
        "Could you elaborate on your medical condition or medications? (e.g., type of condition, how long, any recent changes, specific medications).",
        "How do you feel your medical condition or medication might be impacting your mental well-being?",
        "Have you discussed these mental health symptoms with your doctor or a pharmacist?",
    ],
    'final_check': [
        "Thank you for sharing all of that with me. Is there anything else you'd like to add about your symptoms or situation before I provide a summary and recommendations?",
    ],
    'no_significant_symptoms': [
        "That's wonderful to hear! Based on what you've shared, it seems you're not currently experiencing significant symptoms of depression, anxiety, or stress. Keep up with your self-care practices!",
        "Remember, if anything changes or if you ever feel overwhelmed, PsychQuick is here, and professional help is always available.",
        "Is there anything else you'd like to discuss or ask about your mental well-being today?",
    ],
    'diagnosis_ready': [] # No questions, just a state to indicate readiness
}


# --- Helper Functions ---


def get_severity(score):
    """Determines the severity level based on a given score."""
    # Ensure levels are checked from highest to lowest score
    for level, threshold in sorted(SEVERITY_THRESHOLDS.items(), key=lambda item: item[1], reverse=True):
        if score >= threshold:
            return level
    return 'Minimal'


def generate_acknowledgment(user_input):
    """Generates a friendly and empathetic acknowledgment based on user's input."""
    lower_input = user_input.lower()
    acknowledgments = []


    # General positive/neutral acknowledgments
    if not lower_input.strip(): # For empty responses to follow-ups
        return random.choice([
            "Understood. Let's explore further...",
            "Okay. Moving on...",
            "Thanks for sharing that.",
        ])


    if re.search(r'\b(yes|yeah|ok|true|yup|definitely|alot|a lot|very much)\b', lower_input):
        acknowledgments.append("Understood.")
        acknowledgments.append("Okay, noted.")
        acknowledgments.append("I see.")
        acknowledgments.append("Thank you for confirming.")
    elif re.search(r'\b(no|not really|false|nope|not much|barely)\b', lower_input):
        acknowledgments.append("Okay, noted.")
        acknowledgments.append("Understood.")
        acknowledgments.append("I see.")
        acknowledgments.append("Thanks for clarifying.")
   
    if "thank you" in lower_input or "thanks" in lower_input:
        acknowledgments.append("You're welcome.")
        acknowledgments.append("My pleasure.")


    # Symptom-specific acknowledgments based on keywords in the *current* input
    if re.search(r'\b(sad|depressed|hopeless|down|low mood|unhappy|empty|worthless|guilty)\b', lower_input):
        acknowledgments.append("I hear that feeling low can be incredibly challenging.")
        acknowledgments.append("It sounds like you've been going through a tough time with your mood.")
    if re.search(r'\b(anxious|worry|panic|nervous|on edge|restless|fear)\b', lower_input):
        acknowledgments.append("It sounds like worry has been a significant presence.")
        acknowledgments.append("I understand that anxiety can manifest in many ways.")
    if re.search(r'\b(stressed|overwhelmed|tense|pressure|burnout|exhausted)\b', lower_input):
        acknowledgments.append("I understand that stress can feel very heavy.")
        acknowledgments.append("It sounds like you're carrying a lot of weight right now.")
    if re.search(r'\b(sleep|insomnia|tired|fatigue|unrefreshed|sleepy)\b', lower_input):
        acknowledgments.append("I understand that sleep can be quite elusive when you're struggling.")
        acknowledgments.append("It sounds like your sleep has been quite disrupted.")
    if re.search(r'\b(cope|control|difficulties|helpless|overcome)\b', lower_input):
        acknowledgments.append("It's important to acknowledge how challenging these situations can be.")
        acknowledgments.append("I appreciate you sharing how you're navigating these difficulties.")
    if re.search(r'\b(medical|medication|health|illness)\b', lower_input):
        acknowledgments.append("Thank you for sharing that important health information.")
        acknowledgments.append("Noted, this medical context is very helpful.")
    if re.search(r'\b(suicidal|self-harm|end it all|die)\b', lower_input):
        return "Thank you for your honesty. Your safety is our top priority. We need to address this immediately." # Override other acknowledgments


    # If no specific acknowledgment from symptom words, add general ones
    if not acknowledgments:
        acknowledgments.append("Thank you for sharing that.")
        acknowledgments.append("I appreciate your openness.")
        acknowledgments.append("Understood.")
        acknowledgments.append("Okay.")
        acknowledgments.append("I see.")
        acknowledgments.append("That gives me a clearer picture.")


    # Pick a random acknowledgment from the collected list
    # Use set conversion to remove duplicates before picking
    return random.choice(list(set(acknowledgments)))




# --- Expert System Core Logic ---


def analyze_symptoms(text):
    """
    Analyzes user input for keywords and calculates symptom scores.
    Args:
        text (str): The user's input describing symptoms.
    Returns:
        dict: A dictionary of scores for each symptom category.
    """
    lower_text = text.lower()
    current_input_scores = {
        'depression': 0, 'anxiety': 0, 'stress': 0,
        'sleep': 0, 'perceived_stress': 0,
        'medical_condition': False, 'suicidal_thoughts': False,
    }


    # Iterate through each symptom category and its regex keywords
    for category, keywords_map in SYMPTOM_KEYWORDS.items():
        if category == 'suicidal_thoughts':
            for pattern, score_val in keywords_map.items():
                if re.search(pattern, lower_text):
                    current_input_scores['suicidal_thoughts'] = True
                    # Add a base score to relevant categories for crisis keywords
                    current_input_scores['depression'] += score_val
                    current_input_scores['anxiety'] += score_val
                    current_input_scores['stress'] += score_val
                    break # Only need one suicidal keyword to trigger
        elif category == 'medical_condition':
            for pattern, _ in keywords_map.items():
                if re.search(pattern, lower_text):
                    current_input_scores['medical_condition'] = True
                    break # Only need one medical keyword to trigger
        else:
            for pattern, score_val in keywords_map.items():
                try:
                    if re.search(rf"{pattern}", lower_text):
                        current_input_scores[category] += score_val
                except re.error:
                    print(f"Invalid regex pattern: {pattern}")


    return current_input_scores


def update_session_scores(session_scores, new_scores):
    """Updates accumulated scores in the session with new input scores."""
    for key, value in new_scores.items():
        if isinstance(value, bool):
            session_scores[key] = session_scores[key] or value # Use OR for boolean flags
        else:
            session_scores[key] += value # Accumulate scores
    return session_scores


def get_next_question_or_diagnosis(chat_state, last_user_input):
    """
    Determines the next question to ask or if it's time for a diagnosis.
    Manages the conversational flow, asking specific questions before concluding.
    """
    scores = chat_state['symptom_scores']
    current_question_indices = chat_state.get('question_indices', {
        'depression': 0, 'anxiety': 0, 'stress': 0,
        'sleep': 0, 'perceived_stress': 0, 'medical_condition': 0
    })


    # Crisis check is always first
    if scores['suicidal_thoughts']:
        diagnosis, overall_severity, recommendations = apply_rules(scores)
        return format_response_for_frontend(diagnosis, overall_severity, recommendations)


    acknowledgment = generate_acknowledgment(last_user_input)


    # --- Handle suicidal ideation conditional skip first for *any* stage ---
    # This needs to be checked regardless of the current stage, if the *previous* question was the trigger.
    if chat_state['last_question_suicidal_ideation']:
        lower_input = last_user_input.lower()
        if re.search(r'\b(no|not really|none|nope|never|not at all|i do not|i don\'t|0)\b', lower_input):
            current_question_indices['depression'] = 13 # Skip the conditional follow-up
            chat_state['question_indices'] = current_question_indices
            session.modified = True
           
        chat_state['last_question_suicidal_ideation'] = False # Reset the flag
        session.modified = True


    # --- State Machine Logic ---
   
    # State: AWAITING_FIRST_SYMPTOMATIC_INPUT (new state on first interaction)
    # This state handles the very first user input after the page loads.
    # It checks for initial symptoms and decides where to go next.
    if chat_state['current_stage'] == 'awaiting_first_symptomatic_input':
        # Check if medical condition was mentioned in initial input, or if there's any symptom score
        # If user provides symptoms (any score > 0) OR mentions medical condition in first input,
        # we move past this state.
        if scores['medical_condition'] or sum(v for k,v in scores.items() if isinstance(v, int)) > 0:
            if scores['medical_condition']:
                chat_state['current_stage'] = 'asking_medical_followups'
            else:
                chat_state['current_stage'] = 'asking_symptom_followups'
            session.modified = True
            # No 'return' here, fall through to the next appropriate stage to ask the first relevant question immediately.
        else:
            # If the first input was generic (e.g., "hi"), re-prompt for symptoms.
            return f"{acknowledgment}. To help me understand better, please describe any specific symptoms or feelings you've been experiencing. For example, 'I've been feeling stressed lately' or 'I have trouble sleeping.' You can also mention medical conditions or medications."




    # State: ASKING_MEDICAL_FOLLOWUPS
    if chat_state['current_stage'] == 'asking_medical_followups':
        if current_question_indices['medical_condition'] < len(CONVERSATIONAL_FLOW['medical_condition_followup']):
            q = CONVERSATIONAL_FLOW['medical_condition_followup'][current_question_indices['medical_condition']]
            current_question_indices['medical_condition'] += 1
            chat_state['question_indices'] = current_question_indices
            session.modified = True
            return f"{acknowledgment}\n\n{q}"
        else:
            # All medical questions exhausted, proceed to general symptom follow-ups
            chat_state['current_stage'] = 'asking_symptom_followups'
            session.modified = True
            # Fall through for immediate question


    # State: ASKING_SYMPTOM_FOLLOWUPS
    if chat_state['current_stage'] == 'asking_symptom_followups':
        followup_category_priority = ['depression', 'anxiety', 'stress', 'sleep', 'perceived_stress']
        active_questionable_areas = []
       
        for area in followup_category_priority:
            # Only add to active if score is > 0 OR if it was already asked from and we're just finishing its questions
            # This ensures we ask all questions for detected symptoms.
            if (scores[area] > 0 or current_question_indices[area] > 0) and \
               current_question_indices[area] < len(CONVERSATIONAL_FLOW.get(f'{area}_followup', [])):
                active_questionable_areas.append(area)


        if active_questionable_areas:
            # Logic for round-robin question selection
            next_area_to_ask_index = 0
            if chat_state['last_asked_category'] and chat_state['last_asked_category'] in active_questionable_areas:
                try:
                    last_index = active_questionable_areas.index(chat_state['last_asked_category'])
                    next_area_to_ask_index = (last_index + 1) % len(active_questionable_areas)
                except ValueError:
                    next_area_to_ask_index = 0
           
            area_to_ask = active_questionable_areas[next_area_to_ask_index]
            chat_state['last_asked_category'] = area_to_ask
           
            question_index = current_question_indices[area_to_ask]
            question = CONVERSATIONAL_FLOW[f'{area_to_ask}_followup'][question_index]
           
            if area_to_ask == 'depression' and question_index == 11: # Suicidal ideation question
                chat_state['last_question_suicidal_ideation'] = True
           
            current_question_indices[area_to_ask] += 1
            chat_state['question_indices'] = current_question_indices
            session.modified = True
            return f"{acknowledgment}\n\n{question}"
        else:
            # All symptom follow-ups exhausted, move to final check
            chat_state['current_stage'] = 'final_check_stage'
            session.modified = True
            # Fall through for immediate question


    # State: FINAL_CHECK_STAGE
    if chat_state['current_stage'] == 'final_check_stage':
        if not chat_state.get('final_check_asked'):
            chat_state['final_check_asked'] = True
            session.modified = True
            return f"{acknowledgment}\n\n{CONVERSATIONAL_FLOW['final_check'][0]}"
        else:
            # User has responded to final check, move to diagnosis
            chat_state['current_stage'] = 'diagnosis_ready'
            session.modified = True
            # Fall through to diagnosis.


    # State: DIAGNOSIS_READY
    if chat_state['current_stage'] == 'diagnosis_ready':
        total_symptom_score = sum(v for k, v in scores.items() if isinstance(v, int) and k not in ['suicidal_thoughts', 'medical_condition'])
       
        if total_symptom_score < SEVERITY_THRESHOLDS['Mild'] and not scores['medical_condition']:
            return random.choice(CONVERSATIONAL_FLOW['no_significant_symptoms'])
       
        diagnosis, overall_severity, recommendations = apply_rules(scores)
        return format_response_for_frontend(diagnosis, overall_severity, recommendations)


    # Fallback for unexpected states (should not be reached in normal operation)
    return "I'm sorry, an unexpected error occurred. Let's restart. Please describe any symptoms you are experiencing."




def apply_rules(scores):
    """
    Applies expert system rules to determine diagnosis, severity, and recommendations.
    This function contains at least 50 distinct rules.
    Args:
        scores (dict): The calculated symptom scores.
    Returns:
        tuple: (list of diagnosis, overall severity, list of recommendations)
    """
    diagnosis = []
    recommendations = []
    has_significant_issue = False


    # Calculate individual severities
    depression_severity = get_severity(scores['depression'])
    anxiety_severity = get_severity(scores['anxiety'])
    stress_severity = get_severity(scores['stress'])
    sleep_severity = get_severity(scores['sleep'])
    perceived_stress_severity = get_severity(scores['perceived_stress'])


    # --- Rule Set 1: Immediate Crisis Intervention (Rule 1) ---
    if scores['suicidal_thoughts']:
        diagnosis.append('Immediate Crisis: Suicidal Ideation Detected')
        recommendations.append('It is crucial to seek immediate professional help. Please contact a crisis hotline, emergency services, or go to the nearest emergency room. Your life is valuable, and support is available.')
        recommendations.append('**Malaysia Crisis Hotlines:**')
        for hotline in MALAYSIA_RESOURCES['hotlines']:
            line_info = f"- {hotline['name']}: "
            if "number" in hotline:
                line_info += f"{hotline['number']}"
                if "hours" in hotline:
                    line_info += f" ({hotline['hours']})"
            if "whatsapp" in hotline:
                line_info += f" (WhatsApp: {hotline['whatsapp']})"
            if "website" in hotline:
                line_info += f" [Website]({hotline['website']})"
            recommendations.append(line_info)
        return diagnosis, 'Extremely Severe', recommendations


    # --- Rule Set 2: Individual Symptom Severity (Rules 2-26) ---
    # Depression (Rules 2-6)
    if depression_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Severe': diagnosis.append('Severe Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Moderate': diagnosis.append('Moderate Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Mild': diagnosis.append('Mild Depression Symptoms')
    else: diagnosis.append('Minimal Depression Symptoms') # Rule 6.1


    # Anxiety (Rules 7-11)
    if anxiety_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Severe': diagnosis.append('Severe Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Moderate': diagnosis.append('Moderate Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Mild': diagnosis.append('Mild Anxiety Symptoms')
    else: diagnosis.append('Minimal Anxiety Symptoms') # Rule 11.1


    # Stress (Rules 12-16)
    if stress_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Severe': diagnosis.append('Severe Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Moderate': diagnosis.append('Moderate Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Mild': diagnosis.append('Mild Stress Symptoms')
    else: diagnosis.append('Minimal Stress Symptoms') # Rule 16.1


    # Sleep (Rules 17-21)
    if sleep_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Severe': diagnosis.append('Severe Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Moderate': diagnosis.append('Moderate Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Mild': diagnosis.append('Mild Sleep Disturbance')
    else: diagnosis.append('Minimal Sleep Disturbance') # Rule 21.1


    # Perceived Stress (Rules 22-26)
    if perceived_stress_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Severe': diagnosis.append('Severe Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Moderate': diagnosis.append('Moderate Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Mild': diagnosis.append('Mild Perceived Stress')
    else: diagnosis.append('Minimal Perceived Stress') # Rule 26.1


    # --- Rule Set 3: Co-occurrence and Specific Patterns (Rules 27-30.3) ---
    # Rule 27: Mixed Anxiety-Depressive Disorder (Common Co-occurrence)
    if depression_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       anxiety_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Possible Mixed Anxiety-Depressive Symptoms')
        has_significant_issue = True
    # Rule 28: Stress impacting sleep
    if stress_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       sleep_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Stress-induced Sleep Issues')
        has_significant_issue = True
    # Rule 29: Anxiety impacting sleep
    if anxiety_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       sleep_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Anxiety-induced Sleep Issues')
        has_significant_issue = True
    # Rule 30: Primary concern: Stress Management if stress is dominant
    if stress_severity in ['Moderate', 'Severe'] and all(get_severity(scores[k]) == 'Minimal' for k in ['depression', 'anxiety', 'sleep'] if k != 'stress'):
        diagnosis.append('Primary concern: Stress Management')
    # Rule 30.1: Primary concern: Sleep Health if sleep is dominant
    if sleep_severity in ['Moderate', 'Severe'] and all(get_severity(scores[k]) == 'Minimal' for k in ['depression', 'anxiety', 'stress'] if k != 'sleep'):
        diagnosis.append('Primary concern: Sleep Health')
    # Rule 30.2: Persistent sadness without other major symptoms
    if depression_severity == 'Moderate' and anxiety_severity == 'Minimal' and stress_severity == 'Minimal':
        diagnosis.append('Primary concern: Persistent Sadness/Low Mood')
    # Rule 30.3: High perceived stress with moderate general symptoms
    if perceived_stress_severity in ['Severe', 'Extremely Severe'] and overall_severity == 'Moderate':
        diagnosis.append('High Perceived Stress Impacting Overall Well-being')




    # --- Rule Set 4: Overall Severity Determination (Rules 31-35.3) ---
    overall_severity = 'Minimal'
    severity_order = ['Minimal', 'Mild', 'Moderate', 'Severe', 'Extremely Severe']
    current_max_index = 0


    for sev in [depression_severity, anxiety_severity, stress_severity, sleep_severity, perceived_stress_severity]:
        index = severity_order.index(sev)
        if index > current_max_index:
            current_max_index = index
    overall_severity = severity_order[current_max_index]


    # Rule 35.1: If no specific diagnosis but some scores are not minimal
    if not has_significant_issue and overall_severity != 'Minimal' and not diagnosis:
        diagnosis.append('General Mild Discomfort')
    # Rule 35.2: If multiple severe symptoms
    if sum(1 for s in [depression_severity, anxiety_severity, stress_severity] if s in ['Severe', 'Extremely Severe']) >= 2:
        diagnosis.append('Complex Presentation with Multiple Severe Symptoms')
        overall_severity = 'Extremely Severe' # Elevate overall severity
    # Rule 35.3: If all major categories are at least moderate
    if all(get_severity(scores[k]) in ['Moderate', 'Severe', 'Extremely Severe'] for k in ['depression', 'anxiety', 'stress']):
        diagnosis.append('Widespread Moderate to Severe Symptoms')
        if overall_severity in ['Mild', 'Moderate']: # Ensure severity is elevated if not already
            overall_severity = 'Severe'


    # --- Rule Set 5: Recommendations based on Overall Severity (Rules 36-50.1) ---


    # Rule 36: General recommendation for any level of concern
    if overall_severity != 'Minimal':
        recommendations.append('It\'s important to take care of your mental well-being.')


    # --- Rule Set 6: Specific Issue Recommendations (Rules 51-70) ---


    # Depression Specific Recommendations (Rules 51-54)
    if depression_severity == 'Mild':
        recommendations.append(["Stay connected : socializing with friends and family.",
                                "Exercise regularly : briskwalking, jogging, or swimming can relax your mind and releases endorphins.",
                                "Mantained a balanced diet : eating nutritious meals can support overall well-being.",
                                "Enough sleep : getting enough rest is important for your mind.",
                                "Practice mindfulness : techniques like meditation or deep breathing can help manage stress.",
                                "Limit caffeine : reducing the intake of caffein can prevent mood fluctuations.",
                                "Engage in enjoyable activites : trying new hobbies can make life worth living again.",
                                "Seek professional support : therapy or counselling can provide guidance tailored to individual needs."])
    elif depression_severity == 'Moderate':
        recommendations.append(["Psychotheraphy : cognitive behavioral therapy helps in managing thought patterns and behaviours.",
                                "Medication (if needed) : antidepressants could help if your symptoms significantly impact daily life.",
                                "Structured routine : mantain a consistent schedule for sleep, meals, and activities can help stabilize mood.",
                                "Exercise : physical activity such as hiking, jogging, or swimming can improve symptoms by boosting endorphins.",
                                "Social support : talk and engage with friends, family, or support groups to relief emotional tentions.",
                                "Relaxation techniques : medication or deep breathing is proven effective in managing stress.",
                                "Professional guidance : consulting a mental health professional ensures tailored treatment."])
    elif depression_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Psychotheraphy : cognitive behavioral therapy (CBT) is highly effective for severe depression.",
                                "Medication : antidepressants may be necessary to help manage symptoms.",
                                "Hospitalization (if needed) : in cases of severe risk to self or others, inpatient care may be required.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Support networks : engage with support groups or community resources for additional help.",
                                "Emergency contacts : have a plan in place for immediate support if suicidal thoughts intensify."])


    # Anxiety Specific Recommendations (Rules 55-58)
    if anxiety_severity == 'Mild':
        recommendations.append(["Regular exercise : physical activity can help regulate stress hormones and boosts mood.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation.",
                                "Healthy lifestyle : maintain a balanced diet, get enough sleep, and limit caffeine intake.",
                                "Journaling : writing down your thoughts can help process feelings and reduce anxiety.",
                                "Gradual exposure : slowly facing feared situations can help desensitize anxiety responses.",
                                "Support network : talk to friends or family about your feelings to gain perspective."])
    elif anxiety_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge anxious thought patterns.",
                                "Medication (if needed) : anti-anxiety medications can help manage symptoms.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep is sufficient to regulate and stabilize hormones.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce anxiety.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Deep brething exercises : techniques like diaphragmatic breathing can help calm the nervous system.",
                                "Journaling : writing about your feelings can help process anxiety and identify triggers."])
    elif anxiety_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Exposure Therapy with a licensed therapist is highly recommended.",
                                "Medication : anti-anxiety medications may be necessary to manage severe symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if anxiety becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe anxiety leading to functional impairment or risk of harm."])


    # Stress Specific Recommendations (Rules 59-62)
    if stress_severity == 'Mild':
        recommendations.append(["Take regular breaks : short breaks during work, study, or using social media can help refresh your mind.",
                                "Practice relaxation techniques : deep breathing, meditation, or yoga can reduce stress levels.",
                                "Time management : prioritize tasks and set realistic goals to avoid feeling overwhelmed.",
                                "Healthy lifestyle : regular exercise, balanced diet, and sufficient sleep are essential for managing stress.",
                                "Social support : talk to friends or family about your stressors to gain perspective and support.",
                                "Engage in enjoyable activities : hobbies or leisure activities can provide a much-needed distraction from stress.",
                                "Practice gratitude : focusing on positive aspects of life can help shift your mindset away from stressors.",
                                "Limit exposure to stressors : identify and reduce sources of stress in your environment, such as negative news or toxic relationships."])
    elif stress_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge unhelpful thought patterns contributing to stress.",
                                "Time management skills : learning to prioritize tasks and set realistic goals can help reduce feelings of being overwhelmed.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce stress.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep are crucial for managing stress.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation."])
    elif stress_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Stress Management Therapy with a licensed therapist is highly recommended.",
                                "Medication (if needed) : anti-anxiety or antidepressant medications may be necessary to manage severe stress symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if stress becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe stress leading to functional impairment or risk of harm."])


    # Sleep Specific Recommendations (Rules 63-66)
    if sleep_severity == 'Mild':
        recommendations.append(["Mantain a consistent sleep schedule : go to bed and wake up at the same time every day, even on weekends.",
                                "Create a relaxing bedtime routine : engage in calming activities before sleep, such as reading or taking a warm bath.",
                                "Limit screen time : avoid screens at least 30 minutes before bed to reduce blue light exposure.",
                                "Create a comfortable sleep environment : ensure your bedroom is dark, quiet, and at a comfortable temperature.",
                                "Avoid stimulants : limit caffeine and nicotine intake, especially in the afternoon and evening.",
                                "Exercise regularly : physical activity during the day can help improve sleep quality, but avoid vigorous exercise close to bedtime.",
                                "Manage stress : practice relaxation techniques like deep breathing or meditation to calm your mind before sleep."])
    elif sleep_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy for Insomnia (CBT-I) : a structured program that helps identify and change thoughts and behaviors that cause or worsen sleep problems.",
                                "Sleep hygiene education : learn about good sleep practices, such as maintaining a consistent sleep schedule and creating a restful environment.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can help reduce anxiety and promote better sleep.",
                                "Limit naps : avoid long daytime naps, especially in the afternoon, to improve nighttime sleep quality.",
                                "Medication (if needed) : short-term use of sleep aids may be considered under medical supervision, but should not be the first line of treatment."])
    elif sleep_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy for Insomnia (CBT-I) with a licensed therapist is highly recommended.",
                                "Medication (if needed) : prescription sleep aids may be necessary to manage severe sleep disturbances, but should be used under medical supervision.",
                                "Sleep studies : in some cases, a sleep study may be needed to diagnose underlying sleep disorders such as sleep apnea.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe insomnia leading to functional impairment or risk of harm."])


    # Perceived Stress Specific Recommendations (Rules 67-70)
    if perceived_stress_severity == 'Mild':
        recommendations.append(["Practice relaxation techniques : deep breathing, meditation, or yoga can help reduce perceived stress levels.",
                                "Time management : prioritize tasks and set realistic goals to avoid feeling overwhelmed.",
                                "Healthy lifestyle : regular exercise, balanced diet, and sufficient sleep are essential for managing perceived stress.",
                                "Social support : talk to friends or family about your stressors to gain perspective and support.",
                                "Engage in enjoyable activities : hobbies or leisure activities can provide a much-needed distraction from stress.",
                                "Practice gratitude : focusing on positive aspects of life can help shift your mindset away from stressors.",
                                "Limit exposure to stressors : identify and reduce sources of stress in your environment, such as negative news or toxic relationships."])
    elif perceived_stress_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge unhelpful thought patterns contributing to perceived stress.",
                                "Time management skills : learning to prioritize tasks and set realistic goals can help reduce feelings of being overwhelmed.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce perceived stress.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep are crucial for managing perceived stress.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation."])
    elif perceived_stress_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Stress Management Therapy with a licensed therapist is highly recommended.",
                                "Medication (if needed) : anti-anxiety or antidepressant medications may be necessary to manage severe perceived stress symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if perceived stress becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe perceived stress leading to functional impairment or risk of harm."])


    # Holistic well-being (Rule 71)
    if overall_severity != 'Minimal':
        recommendations.append('Remember that mental health is as important as physical health. Be kind to yourself and seek support when needed. Prioritize self-care and open communication with trusted individuals.')
   
    # If only minimal symptoms across the board (Rule 72)
    if overall_severity == 'Minimal' and not has_significant_issue and not diagnosis:
        recommendations.append('Continue to monitor your well-being. Maintaining a healthy lifestyle, including regular exercise, balanced nutrition, and sufficient sleep, is key for mental resilience. Pay attention to early signs of stress or low mood.')




    # --- Rule Set 7: Contraindication and Malaysia-Specific Resources (Rules 73-77) ---
    # Rule 73: Contraindication rule (medical conditions)
    if scores['medical_condition']:
        recommendations.insert(0, '**Important Note:** Given your mention of a medical condition/medication, it is crucial to consult with your primary care physician or a specialist first. They can help determine if your symptoms are related to your physical health or medication, and ensure any mental health recommendations are safe and appropriate for your overall health. Always discuss mental health concerns with them.')


    # Rule 74: General Malaysia Hotlines (Always include if not Minimal)
    if overall_severity != 'Minimal':
        recommendations.append('\n**Malaysia Mental Health Hotlines:**')
        for hotline in MALAYSIA_RESOURCES['hotlines']:
            line_info = f"- {hotline['name']}: "
            if "number" in hotline:
                line_info += f"{hotline['number']}"
                if "hours" in hotline:
                    line_info += f" ({hotline['hours']})"
            if "whatsapp" in hotline:
                line_info += f" (WhatsApp: {hotline['whatsapp']})"
            if "website" in hotline:
                line_info += f" [Website]({hotline['website']})"
            recommendations.append(line_info)


    # Rule 75: Guidance on finding therapists in Malaysia (Always include if not Minimal)
    if overall_severity != 'Minimal':
        recommendations.append('\n**Finding a Therapist in Malaysia:**')
        for guidance in MALAYSIA_RESOURCES['therapist_guidance']:
            recommendations.append(f"- {guidance}")


    # Rule 76: Encourage follow-up
    recommendations.append('\n')
    recommendations.append('This system provides general guidance. For a comprehensive assessment and personalized treatment plan, always consult with a qualified mental health professional.')
    # Rule 77: Disclaimer for automated system
    recommendations.append('Remember, PsychQuick is an automated system and not a substitute for professional medical or psychological advice. It is designed to provide preliminary insights and connect you with resources.')
    # Rule 78: Encourage open communication
    recommendations.append('Don\'t hesitate to talk to someone you trust about how you\'re feeling. Sharing your experiences can be a powerful first step towards healing.')


    return diagnosis, overall_severity, recommendations


# Helper to format the final response for the frontend
def format_response_for_frontend(diagnosis, overall_severity, recommendations):
    response_text = ""
    if diagnosis:
        # Filter out "Minimal" symptoms from the diagnosis list to keep it concise and focused
        filtered_diagnosis = [d for d in diagnosis if not d.startswith('Minimal')]
        if filtered_diagnosis:
            response_text += f"**Potential Areas of Concern:** {', '.join(filtered_diagnosis)}\n\n"
        else:
            response_text += "**No significant concerns identified based on the provided symptoms.**\n\n"
    else:
        response_text += "**No significant concerns identified based on the provided symptoms.**\n\n"


    response_text += f"**Overall Severity:** {overall_severity}\n\n"
    response_text += "**Recommendations:**\n"
    for rec in recommendations:
        response_text += f"- {rec}\n"
    return response_text


# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main chat interface and initializes session."""
    # Reset session on fresh page load to start a new conversation
    session.clear()
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').strip()
    exit_keywords = ['stop', 'quit', 'end', 'exit', "that's all", 'no more']
    if any(word in user_input.lower() for word in exit_keywords):
        chat_state = session.get('chat_state')
        if chat_state:
            scores = chat_state.get('symptom_scores', {})
            diagnosis, overall_severity, recommendations = apply_rules(scores)
            session.clear()
            final_response = format_response_for_frontend(diagnosis, overall_severity, recommendations)
            final_response += "\n\n_You chose to end the chat. Thank you for using PsychQuick._ 💙"
            return jsonify({"response": final_response})
        else:
            return jsonify({"response": "Session ended. Thank you for using PsychQuick. 💙"})

   
    # Initialize session state if it's a new conversation or session cleared
    if 'chat_state' not in session or not session['chat_state']:
        session['chat_state'] = {
            'current_stage': 'awaiting_first_symptomatic_input', # Initial state on first interaction
            'symptom_scores': {
                'depression': 0, 'anxiety': 0, 'stress': 0,
                'sleep': 0, 'perceived_stress': 0,
                'medical_condition': False, 'suicidal_thoughts': False,
            },
            'question_indices': { # Track current question index for each category
                'depression': 0, 'anxiety': 0, 'stress': 0,
                'sleep': 0, 'perceived_stress': 0, 'medical_condition': 0
            },
            'last_asked_category': None, # Track the last symptom category a question was asked from
            'last_question_suicidal_ideation': False, # Flag if the last question asked was the suicidal ideation prompt
        }


    chat_state = session['chat_state']

    # Process user input and update scores
    if user_input:
        new_scores = analyze_symptoms(user_input)
        chat_state['symptom_scores'] = update_session_scores(chat_state['symptom_scores'], new_scores)
        session.modified = True # Mark session as modified


    # Determine next action (question or diagnosis)
    response_text = get_next_question_or_diagnosis(chat_state, user_input)


    # Simulate processing time
    time.sleep(1.0)


    return jsonify({"response": response_text})



app = Flask(__name__, static_folder='static', template_folder='templates')
# A secret key is REQUIRED for Flask sessions to work.
# In a real application, this should be a strong, randomly generated key stored securely (e.g., environment variable).
app.secret_key = os.urandom(24)


# --- Configuration and Data ---


# Keywords and their scores for different symptom categories
# Increased score values to make symptoms more impactful for triggering follow-ups
SYMPTOM_KEYWORDS = {
    'depression': {
        r'\bsad\b': 5, r'\bdown\b': 5, r'\bhopeless\b': 5, r'\bdepressed\b': 5,
        r'\btired\b': 3, r'\bfatigue\b': 3, r'\blow energy\b': 3,
        r'\blost interest\b': 5, r'\bno pleasure\b': 5, r'\banhedonia\b': 5,
        r'\bworthless\b': 4, r'\bguilty\b': 4, r'\bcrying\b': 3, r'\bempty\b': 3,
        r'\bappetite change\b': 2, r'\bweight change\b': 2, r'\cry\b': 3,
        r'\bdifficulty concentrating\b': 2, r'\bmind is blank\b': 2,
        r'\bno motivation\b': 3, r'\bfeeling numb\b': 3,
    },
    'anxiety': {
        r'\bworry\b': 5, r'\banxious\b': 5, r'\bnervous\b': 5, r'\brestless\b': 5,
        r'\bpanic\b': 5, r'\bfear\b': 5, r'\bdread\b': 5,
        r'\bheart racing\b': 4, r'\bshortness of breath\b': 4, r'\bsweating\b': 3,
        r'\birritable\b': 3, r'\bon edge\b': 3, r'\bconstant worry\b': 5,
        r'\bavoiding\b': 2, r'\bshaking\b': 3, r'\btrembling\b': 3,
        r'\bunease\b': 3, r'\bchest pain\b': 3, r'\bnausea\b': 2,
    },
    'stress': {
        r'\bstressed\b': 5, r'\boverwhelmed\b': 5, r'\btense\b': 5, r'\bburnout\b': 5,
        r'\bdifficulty relaxing\b': 3, r'\bcan\'t switch off\b': 3,
        r'\bfrustrated\b': 3, r'\bimpatient\b': 3,
        r'\bheadache\b': 2, r'\bmuscle tension\b': 2,
        r'\bpressure\b': 3, r'\bdemands\b': 3, r'\bexhausted\b': 3, r'\bfeeling drained\b': 3,
    },
    'sleep': { # Reflects SSS (Sleep Symptom Scale) concepts
        r'\binsomnia\b': 5, r'\bdifficulty sleeping\b': 5, r'\bcan\'t fall asleep\b': 5,
        r'\bwaking up early\b': 4, r'\bwaking often\b': 4, r'\btrouble sleeping\b': 5,
        r'\bnot refreshed\b': 4, r'\bpoor quality sleep\b': 4, r'\bsleep problems\b': 5,
        r'\bdaytime sleepiness\b': 3, r'\bsleeping too much\b': 3, r'\bsleep deprived\b': 4,
    },
    'perceived_stress': { # Reflects PSS (Perceived Stress Scale) concepts
        r'\bunable to cope\b': 5, r'\bthings are out of control\b': 5, r'\bcan\'t handle\b': 5,
        r'\bdifficulties piling up\b': 4, r'\bnervous about demands\b': 4, r'\boverload\b': 4,
        r'\bfeeling helpless\b': 4,
    },
    'suicidal_thoughts': {
        r'\bsuicidal\b': 20, r'\bend it all\b': 20, r'\bharm myself\b': 20, r'\bkill myself\b': 20,
        r'\bwant to die\b': 20, r'\bnot want to live\b': 20, r'\bself-harm\b': 20,
    },
    'medical_condition': {
        r'\bmedical condition\b': 10, r'\bmedication\b': 10, r'\bdiabetes\b': 10, r'\bheart disease\b': 10,
        r'\bthyroid\b': 10, r'\bchronic illness\b': 10, r'\bphysical illness\b': 10,
        r'\bpre-existing condition\b': 10, r'\btaking pills\b': 10, r'\bhealth issue\b': 10,
    }
}


# Severity thresholds
SEVERITY_THRESHOLDS = {
    'Extremely Severe': 25, # Adjusted thresholds for new scoring
    'Severe': 15,
    'Moderate': 8,
    'Mild': 3,
    'Minimal': 0,
}


# Malaysia-specific hotlines and resources
MALAYSIA_RESOURCES = {
    'hotlines': [
        {"name": "Befrienders Kuala Lumpur", "number": "03-7956 8145", "hours": "24 hours", "website": "https://www.befrienders.org.my/"},
        {"name": "Befrienders Penang", "number": "04-281 5161", "hours": "3pm - midnight", "website": "https://www.befrienders.org.my/centre-in-malaysia"},
        {"name": "Befrienders Ipoh", "number": "05-547 7933", "hours": "4pm - 11pm", "website": "https://www.befrienders.org.my/centre-in-malaysia"},
        {"name": "Malaysian Mental Health Association (MMHA)", "number": "03-2780 6803", "hours": "Mon-Fri, 10am-5pm", "website": "https://mmha.org.my/"},
        {"name": "Talian Kasih", "number": "15999 or WhatsApp +60192615999", "hours": "24 hours", "website": "https://www.kpwkm.gov.my/"},
        {"name": "MIASA Crisis Helpline", "number": "1-800-180-066", "hours": "24/7", "website": "https://www.miasa.org.my/"},
        {"name": "RELATE Malaysia (online psychotherapy)", "website": "https://relate.com.my/"},
        {"name": "SOLS Health", "number": "6018-664-0247", "website": "https://www.sols247.org/solshealth"},
        {"name": "Life Line Association Malaysia", "number": "03-42657995", "website": "http://lifeline.org.my/cn/"},
        {"name": "Women's Aid Organization (WAO)", "number": "+603 7956 3488", "whatsapp": "+6018 988 8058", "website": "https://wao.org.my/"},
    ],
    'therapist_guidance': [
        "You can find qualified therapists through the Ministry of Health's search portal: https://mhps.moh.gov.my/SEARCH/",
        "The Malaysian Society of Clinical Psychology (MSCP) also maintains a directory: https://www.mscp.my/clinical-psychologist-registry",
        "The Malaysian Mental Health Association (MMHA) provides psychological therapy services, sometimes with financial subsidies: https://mmha.org.my/find-help",
        "Consider governmental health clinics (Klinik Kesihatan) for referrals to public hospital psychiatric departments, which are often more affordable.",
        "Online platforms like ThoughtFull.world also list therapists in Malaysia: https://www.thoughtfull.world/professionals/therapy-near-me-malaysia",
        "TherapyRoute.com also lists psychologists, counsellors, & therapists in Malaysia: https://www.therapyroute.com/therapists/malaysia/1",
    ]
}


# Define conversational stages and follow-up questions
# Significantly expanded and refined questions for more in-depth conversation
CONVERSATIONAL_FLOW = {
    'general_prompt': "Please describe any symptoms you are experiencing. For example, 'I feel sad and tired all the time.' or 'I worry a lot about the future.'",
    'initial_medical_check_question': "Do you have any pre-existing medical conditions or are you currently taking any medications? (This helps me provide safer recommendations.)",
    'depression_followup': [
        "On a scale of 0 to 3 (0=Did not apply to me at all, 1=Applied to me to some degree, or some of the time, 2=Applied to me to a considerable degree, or a good part of time, 3=Applied to me very much, or most of the time): How much did you feel that you couldn't seem to experience any positive feeling at all?", # DASS-like
        "How often have you found it difficult to get started on things you needed to do?", # DASS-like
        "Have you felt that life was meaningless or that you had nothing to look forward to?", # DASS-like
        "How frequently have you felt down-hearted and blue?", # DASS-like
        "Have you experienced any changes in your interest in activities you once enjoyed?", # DASS-like, broader
        "On a scale of 1 to 10, how would you rate your overall mood on most days (1 being very low, 10 being very high)?",
        "How has your ability to feel pleasure or joy been lately? Is it difficult to find enjoyment in things?",
        "Have you noticed changes in your sleep patterns (e.g., sleeping too much, too little, difficulty staying asleep)?",
        "How has your appetite been, and have you experienced any significant weight changes without trying?",
        "Do you often feel restless or slowed down in your movements or speech, so much that others have noticed?",
        "How frequently do you have thoughts that you are a failure or that you have let yourself or your family down?",
        "Have you had recurrent thoughts of death, or any thoughts of harming yourself? (Please answer honestly, your safety is paramount.)", # Suicidal ideation question (Index 11)
        "If you answered 'yes' to the previous question, have you taken any steps or made any preparations toward those thoughts?", # Critical follow-up (Index 12)
        "Can you describe a typical day for you recently, focusing on your energy levels and mood throughout the day?",
        "What kind of thoughts typically run through your mind when you're feeling sad or down?",
        "Have you found yourself isolating from others, or avoiding social interactions more than usual?",
        "Is there a particular time of day when your mood tends to be at its lowest?",
        "What activities, if any, still bring you a sense of relief or small moments of happiness?",
        "How has your concentration or ability to focus on tasks been affected?",
        "Do you find yourself dwelling on past events, or feeling excessive guilt or remorse?",
        "Are there any specific situations or events that seem to trigger or worsen your low mood?",
        "How would you describe your self-esteem and self-worth lately?",
    ],
    'anxiety_followup': [
        "On a scale of 0 to 3: How much did you feel you were close to panic?", # DASS-like
        "How often have you been aware of dryness of your mouth, or difficulty breathing?", # DASS-like physical symptoms
        "Have you experienced any sudden feelings of intense fear, terror, or apprehension, sometimes with a racing heart, sweating, or dizziness?", # Panic attack type questions
        "How often do you find yourself worrying excessively about a variety of things, even small daily issues?",
        "Do you often feel keyed up, on edge, or restless?",
        "How much difficulty do you have relaxing or calming down?",
        "Do you find yourself avoiding certain situations, places, or activities because you anticipate feeling anxious or having a panic attack?",
        "How often do you experience a racing heart, trembling, or shortness of breath when you're feeling anxious?",
        "Has your anxiety caused you significant distress or impairment in social, occupational, or other important areas of functioning?",
        "How long have you been experiencing these anxious feelings, and are they present most days?",
        "Can you describe a recent situation where you felt particularly anxious? What happened?",
        "What kind of thoughts typically accompany your anxious feelings?",
        "Do you experience physical symptoms like muscle tension, headaches, or stomach issues when you're anxious?",
        "How much do you worry about future events, even those that are unlikely to happen?",
        "Do you find it hard to control your worrying once it starts?",
        "Have you had any experiences where you felt a sudden, overwhelming surge of intense fear or discomfort, often called a 'panic attack'?",
        "Do you ever feel a sense of impending doom or danger without a clear reason?",
        "How does your anxiety affect your ability to sleep or eat?",
        "What strategies do you currently use to try and manage your anxiety?",
        "Do you ever feel detached from your body or your surroundings when you're anxious?",
    ],
    'stress_followup': [
        "On a scale of 0 to 3: How much did you tend to over-react to situations?", # DASS-like
        "How often have you found it hard to wind down after a busy day?", # DASS-like
        "How much did you feel that you were rather touchy or easily irritated?", # DASS-like
        "Do you often feel that you are unable to control the important things in your life, or that difficulties are piling up?", # PSS-like
        "How often have you felt nervous and 'stressed out' because of demands on your time or energy?", # PSS-like
        "How often do you feel overwhelmed by your responsibilities?",
        "Have you noticed physical symptoms like chronic headaches, muscle tension, or digestive issues that you link to stress?",
        "How has your stress affected your relationships, work performance, or academic progress?",
        "What are the main sources of stress in your life right now? Can you list a few?",
        "What coping strategies do you typically use when you feel stressed, and how effective are they?",
        "How often do you feel that you cannot cope with all the things that you have to do?",
        "Do you feel that you are on top of things, or often feel overwhelmed?",
        "How effectively have you been able to control irritations in your life?",
        "How often have you felt that things were going your way recently?",
        "Do you find yourself procrastinating more when you're stressed?",
        "How does stress impact your decision-making abilities?",
        "Have you noticed changes in your appetite or eating habits due to stress?",
        "Do you feel more physically fatigued when you're under stress?",
        "How do you typically wind down or relax after a stressful period?",
        "Are there any specific situations or people that consistently trigger your stress?",
    ],
    'sleep_followup': [
        "On a scale of 0 to 3: How much did you find it difficult to fall asleep?", # SSS-like
        "How often do you wake up earlier than desired, or wake up frequently during the night?", # SSS-like
        "Do you feel unrefreshed or tired even after what seems like a full night's sleep?", # SSS-like
        "On average, how many hours of sleep do you get per night?",
        "How would you rate the overall quality of your sleep (e.g., restless, deep, interrupted)?",
        "Has your sleep problem been ongoing for more than a month? If so, for how long?",
        "Does your sleep issue significantly impact your daytime functioning, energy levels, or mood?",
        "Are there specific thoughts or worries that keep you awake at night?",
        "Do you have a consistent bedtime and wake-up time, even on weekends?",
        "What strategies have you already tried to improve your sleep, and what were the results?",
        "How long does it typically take you to fall asleep once you get into bed?",
        "Do you often wake up feeling tired even after a full night's sleep?",
        "How frequently do you wake up during the night and have difficulty falling back asleep?",
        "Do you experience restless legs or any other physical discomfort that interferes with your sleep?",
        "How often do you feel drowsy or fall asleep unintentionally during the day (e.g., while watching TV, reading, or driving)?",
        "What does your bedtime routine typically look like? (e.g., screen time, food/drink, activities)",
        "Is your sleep environment dark, quiet, and cool?",
        "Do you consume caffeine or alcohol, especially in the hours leading up to bedtime?",
        "Have you ever been told you snore loudly or stop breathing during sleep?",
        "How has your sleep problem affected your ability to concentrate, your memory, or your overall performance?",
    ],
    'perceived_stress_followup': [
        "On a scale of 0 to 4 (0=Never, 1=Almost Never, 2=Sometimes, 3=Fairly Often, 4=Very Often): How often have you been upset because of something that happened unexpectedly?", # PSS question
        "How often have you felt that you were unable to control the important things in your life?", # PSS question
        "How often have you felt nervous and 'stressed'?", # PSS question
        "How often have you dealt successfully with irritating life hassles?", # PSS question, reversed score potential
        "How often have you felt that you were effectively coping with important changes that were occurring in your life?", # PSS question, reversed score potential
        "How often have you felt confident about your ability to handle your personal problems?", # PSS question, reversed score potential
        "How often have you felt that things were going your way?", # PSS question, reversed score potential
        "How often have you found that you could not cope with all the things that you had to do?", # PSS question
        "How often have you been able to control irritations in your life?", # PSS question, reversed score potential
        "How often have you felt that you were on top of things?", # PSS question, reversed score potential
        "How often do you feel that personal difficulties are piling up so high that you cannot overcome them?",
        "In the last month, how often have you felt that you were unable to control the important things in your life?",
        "How often in the last month have you felt confident about your ability to handle your personal problems?",
        "How often in the last month have you felt that difficulties were piling up so high that you could not overcome them?",
        "How often in the last month have you felt that you were unable to cope with all the things that you had to do?",
        "How often in the last month have you felt that you were on top of things?",
        "How often in the last month have you been angered because of things that happened that were out of your control?",
        "How often in the last month have you felt that you were dealing effectively with the changes in your life?",
        "How often in the last month have you found yourself thinking about things that you have to accomplish?",
        "How often in the last month have you felt that you were able to control irritations in your life?",
    ],
    'medical_condition_followup': [
        "Could you elaborate on your medical condition or medications? (e.g., type of condition, how long, any recent changes, specific medications).",
        "How do you feel your medical condition or medication might be impacting your mental well-being?",
        "Have you discussed these mental health symptoms with your doctor or a pharmacist?",
    ],
    'final_check': [
        "Thank you for sharing all of that with me. Is there anything else you'd like to add about your symptoms or situation before I provide a summary and recommendations?",
    ],
    'no_significant_symptoms': [
        "That's wonderful to hear! Based on what you've shared, it seems you're not currently experiencing significant symptoms of depression, anxiety, or stress. Keep up with your self-care practices!",
        "Remember, if anything changes or if you ever feel overwhelmed, PsychQuick is here, and professional help is always available.",
        "Is there anything else you'd like to discuss or ask about your mental well-being today?",
    ],
    'diagnosis_ready': [] # No questions, just a state to indicate readiness
}


# --- Helper Functions ---


def get_severity(score):
    """Determines the severity level based on a given score."""
    # Ensure levels are checked from highest to lowest score
    for level, threshold in sorted(SEVERITY_THRESHOLDS.items(), key=lambda item: item[1], reverse=True):
        if score >= threshold:
            return level
    return 'Minimal'


def generate_acknowledgment(user_input):
    """Generates a friendly and empathetic acknowledgment based on user's input."""
    lower_input = user_input.lower()
    acknowledgments = []


    # General positive/neutral acknowledgments
    if not lower_input.strip(): # For empty responses to follow-ups
        return random.choice([
            "Understood. Let's explore further...",
            "Okay. Moving on...",
            "Thanks for sharing that.",
        ])


    if re.search(r'\b(yes|yeah|ok|true|yup|definitely|alot|a lot|very much)\b', lower_input):
        acknowledgments.append("Understood.")
        acknowledgments.append("Okay, noted.")
        acknowledgments.append("I see.")
        acknowledgments.append("Thank you for confirming.")
    elif re.search(r'\b(no|not really|false|nope|not much|barely)\b', lower_input):
        acknowledgments.append("Okay, noted.")
        acknowledgments.append("Understood.")
        acknowledgments.append("I see.")
        acknowledgments.append("Thanks for clarifying.")
   
    if "thank you" in lower_input or "thanks" in lower_input:
        acknowledgments.append("You're welcome.")
        acknowledgments.append("My pleasure.")


    # Symptom-specific acknowledgments based on keywords in the *current* input
    if re.search(r'\b(sad|depressed|hopeless|down|low mood|unhappy|empty|worthless|guilty)\b', lower_input):
        acknowledgments.append("I hear that feeling low can be incredibly challenging.")
        acknowledgments.append("It sounds like you've been going through a tough time with your mood.")
    if re.search(r'\b(anxious|worry|panic|nervous|on edge|restless|fear)\b', lower_input):
        acknowledgments.append("It sounds like worry has been a significant presence.")
        acknowledgments.append("I understand that anxiety can manifest in many ways.")
    if re.search(r'\b(stressed|overwhelmed|tense|pressure|burnout|exhausted)\b', lower_input):
        acknowledgments.append("I understand that stress can feel very heavy.")
        acknowledgments.append("It sounds like you're carrying a lot of weight right now.")
    if re.search(r'\b(sleep|insomnia|tired|fatigue|unrefreshed|sleepy)\b', lower_input):
        acknowledgments.append("I understand that sleep can be quite elusive when you're struggling.")
        acknowledgments.append("It sounds like your sleep has been quite disrupted.")
    if re.search(r'\b(cope|control|difficulties|helpless|overcome)\b', lower_input):
        acknowledgments.append("It's important to acknowledge how challenging these situations can be.")
        acknowledgments.append("I appreciate you sharing how you're navigating these difficulties.")
    if re.search(r'\b(medical|medication|health|illness)\b', lower_input):
        acknowledgments.append("Thank you for sharing that important health information.")
        acknowledgments.append("Noted, this medical context is very helpful.")
    if re.search(r'\b(suicidal|self-harm|end it all|die)\b', lower_input):
        return "Thank you for your honesty. Your safety is our top priority. We need to address this immediately." # Override other acknowledgments


    # If no specific acknowledgment from symptom words, add general ones
    if not acknowledgments:
        acknowledgments.append("Thank you for sharing that.")
        acknowledgments.append("I appreciate your openness.")
        acknowledgments.append("Understood.")
        acknowledgments.append("Okay.")
        acknowledgments.append("I see.")
        acknowledgments.append("That gives me a clearer picture.")


    # Pick a random acknowledgment from the collected list
    # Use set conversion to remove duplicates before picking
    return random.choice(list(set(acknowledgments)))




# --- Expert System Core Logic ---


def analyze_symptoms(text):
    """
    Analyzes user input for keywords and calculates symptom scores.
    Args:
        text (str): The user's input describing symptoms.
    Returns:
        dict: A dictionary of scores for each symptom category.
    """
    lower_text = text.lower()
    current_input_scores = {
        'depression': 0, 'anxiety': 0, 'stress': 0,
        'sleep': 0, 'perceived_stress': 0,
        'medical_condition': False, 'suicidal_thoughts': False,
    }


    # Iterate through each symptom category and its regex keywords
    for category, keywords_map in SYMPTOM_KEYWORDS.items():
        if category == 'suicidal_thoughts':
            for pattern, score_val in keywords_map.items():
                if re.search(pattern, lower_text):
                    current_input_scores['suicidal_thoughts'] = True
                    # Add a base score to relevant categories for crisis keywords
                    current_input_scores['depression'] += score_val
                    current_input_scores['anxiety'] += score_val
                    current_input_scores['stress'] += score_val
                    break # Only need one suicidal keyword to trigger
        elif category == 'medical_condition':
            for pattern, _ in keywords_map.items():
                if re.search(pattern, lower_text):
                    current_input_scores['medical_condition'] = True
                    break # Only need one medical keyword to trigger
        else:
            for pattern, score_val in keywords_map.items():
                try:
                    if re.search(rf"{pattern}", lower_text):
                        current_input_scores[category] += score_val
                except re.error:
                    print(f"Invalid regex pattern: {pattern}")


    return current_input_scores


def update_session_scores(session_scores, new_scores):
    """Updates accumulated scores in the session with new input scores."""
    for key, value in new_scores.items():
        if isinstance(value, bool):
            session_scores[key] = session_scores[key] or value # Use OR for boolean flags
        else:
            session_scores[key] += value # Accumulate scores
    return session_scores


def get_next_question_or_diagnosis(chat_state, last_user_input):
    """
    Determines the next question to ask or if it's time for a diagnosis.
    Manages the conversational flow, asking specific questions before concluding.
    """
    scores = chat_state['symptom_scores']
    current_question_indices = chat_state.get('question_indices', {
        'depression': 0, 'anxiety': 0, 'stress': 0,
        'sleep': 0, 'perceived_stress': 0, 'medical_condition': 0
    })


    # Crisis check is always first
    if scores['suicidal_thoughts']:
        diagnosis, overall_severity, recommendations = apply_rules(scores)
        return format_response_for_frontend(diagnosis, overall_severity, recommendations)


    acknowledgment = generate_acknowledgment(last_user_input)


    # --- Handle suicidal ideation conditional skip first for *any* stage ---
    # This needs to be checked regardless of the current stage, if the *previous* question was the trigger.
    if chat_state['last_question_suicidal_ideation']:
        lower_input = last_user_input.lower()
        if re.search(r'\b(no|not really|none|nope|never|not at all|i do not|i don\'t|0)\b', lower_input):
            current_question_indices['depression'] = 13 # Skip the conditional follow-up
            chat_state['question_indices'] = current_question_indices
            session.modified = True
           
        chat_state['last_question_suicidal_ideation'] = False # Reset the flag
        session.modified = True


    # --- State Machine Logic ---
   
    # State: AWAITING_FIRST_SYMPTOMATIC_INPUT (new state on first interaction)
    # This state handles the very first user input after the page loads.
    # It checks for initial symptoms and decides where to go next.
    if chat_state['current_stage'] == 'awaiting_first_symptomatic_input':
        # Check if medical condition was mentioned in initial input, or if there's any symptom score
        # If user provides symptoms (any score > 0) OR mentions medical condition in first input,
        # we move past this state.
        if scores['medical_condition'] or sum(v for k,v in scores.items() if isinstance(v, int)) > 0:
            if scores['medical_condition']:
                chat_state['current_stage'] = 'asking_medical_followups'
            else:
                chat_state['current_stage'] = 'asking_symptom_followups'
            session.modified = True
            # No 'return' here, fall through to the next appropriate stage to ask the first relevant question immediately.
        else:
            # If the first input was generic (e.g., "hi"), re-prompt for symptoms.
            return f"{acknowledgment}. To help me understand better, please describe any specific symptoms or feelings you've been experiencing. For example, 'I've been feeling stressed lately' or 'I have trouble sleeping.' You can also mention medical conditions or medications."




    # State: ASKING_MEDICAL_FOLLOWUPS
    if chat_state['current_stage'] == 'asking_medical_followups':
        if current_question_indices['medical_condition'] < len(CONVERSATIONAL_FLOW['medical_condition_followup']):
            q = CONVERSATIONAL_FLOW['medical_condition_followup'][current_question_indices['medical_condition']]
            current_question_indices['medical_condition'] += 1
            chat_state['question_indices'] = current_question_indices
            session.modified = True
            return f"{acknowledgment}\n\n{q}"
        else:
            # All medical questions exhausted, proceed to general symptom follow-ups
            chat_state['current_stage'] = 'asking_symptom_followups'
            session.modified = True
            # Fall through for immediate question


    # State: ASKING_SYMPTOM_FOLLOWUPS
    if chat_state['current_stage'] == 'asking_symptom_followups':
        followup_category_priority = ['depression', 'anxiety', 'stress', 'sleep', 'perceived_stress']
        active_questionable_areas = []
       
        for area in followup_category_priority:
            # Only add to active if score is > 0 OR if it was already asked from and we're just finishing its questions
            # This ensures we ask all questions for detected symptoms.
            if (scores[area] > 0 or current_question_indices[area] > 0) and \
               current_question_indices[area] < len(CONVERSATIONAL_FLOW.get(f'{area}_followup', [])):
                active_questionable_areas.append(area)


        if active_questionable_areas:
            # Logic for round-robin question selection
            next_area_to_ask_index = 0
            if chat_state['last_asked_category'] and chat_state['last_asked_category'] in active_questionable_areas:
                try:
                    last_index = active_questionable_areas.index(chat_state['last_asked_category'])
                    next_area_to_ask_index = (last_index + 1) % len(active_questionable_areas)
                except ValueError:
                    next_area_to_ask_index = 0
           
            area_to_ask = active_questionable_areas[next_area_to_ask_index]
            chat_state['last_asked_category'] = area_to_ask
           
            question_index = current_question_indices[area_to_ask]
            question = CONVERSATIONAL_FLOW[f'{area_to_ask}_followup'][question_index]
           
            if area_to_ask == 'depression' and question_index == 11: # Suicidal ideation question
                chat_state['last_question_suicidal_ideation'] = True
           
            current_question_indices[area_to_ask] += 1
            chat_state['question_indices'] = current_question_indices
            session.modified = True
            return f"{acknowledgment}\n\n{question}"
        else:
            # All symptom follow-ups exhausted, move to final check
            chat_state['current_stage'] = 'final_check_stage'
            session.modified = True
            # Fall through for immediate question


    # State: FINAL_CHECK_STAGE
    if chat_state['current_stage'] == 'final_check_stage':
        if not chat_state.get('final_check_asked'):
            chat_state['final_check_asked'] = True
            session.modified = True
            return f"{acknowledgment}\n\n{CONVERSATIONAL_FLOW['final_check'][0]}"
        else:
            # User has responded to final check, move to diagnosis
            chat_state['current_stage'] = 'diagnosis_ready'
            session.modified = True
            # Fall through to diagnosis.


    # State: DIAGNOSIS_READY
    if chat_state['current_stage'] == 'diagnosis_ready':
        total_symptom_score = sum(v for k, v in scores.items() if isinstance(v, int) and k not in ['suicidal_thoughts', 'medical_condition'])
       
        if total_symptom_score < SEVERITY_THRESHOLDS['Mild'] and not scores['medical_condition']:
            return random.choice(CONVERSATIONAL_FLOW['no_significant_symptoms'])
       
        diagnosis, overall_severity, recommendations = apply_rules(scores)
        return format_response_for_frontend(diagnosis, overall_severity, recommendations)


    # Fallback for unexpected states (should not be reached in normal operation)
    return "I'm sorry, an unexpected error occurred. Let's restart. Please describe any symptoms you are experiencing."




def apply_rules(scores):
    """
    Applies expert system rules to determine diagnosis, severity, and recommendations.
    This function contains at least 50 distinct rules.
    Args:
        scores (dict): The calculated symptom scores.
    Returns:
        tuple: (list of diagnosis, overall severity, list of recommendations)
    """
    diagnosis = []
    recommendations = []
    has_significant_issue = False


    # Calculate individual severities
    depression_severity = get_severity(scores['depression'])
    anxiety_severity = get_severity(scores['anxiety'])
    stress_severity = get_severity(scores['stress'])
    sleep_severity = get_severity(scores['sleep'])
    perceived_stress_severity = get_severity(scores['perceived_stress'])


    # --- Rule Set 1: Immediate Crisis Intervention (Rule 1) ---
    if scores['suicidal_thoughts']:
        diagnosis.append('Immediate Crisis: Suicidal Ideation Detected')
        recommendations.append('It is crucial to seek immediate professional help. Please contact a crisis hotline, emergency services, or go to the nearest emergency room. Your life is valuable, and support is available.')
        recommendations.append('**Malaysia Crisis Hotlines:**')
        for hotline in MALAYSIA_RESOURCES['hotlines']:
            line_info = f"- {hotline['name']}: "
            if "number" in hotline:
                line_info += f"{hotline['number']}"
                if "hours" in hotline:
                    line_info += f" ({hotline['hours']})"
            if "whatsapp" in hotline:
                line_info += f" (WhatsApp: {hotline['whatsapp']})"
            if "website" in hotline:
                line_info += f" [Website]({hotline['website']})"
            recommendations.append(line_info)
        return diagnosis, 'Extremely Severe', recommendations


    # --- Rule Set 2: Individual Symptom Severity (Rules 2-26) ---
    # Depression (Rules 2-6)
    if depression_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Severe': diagnosis.append('Severe Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Moderate': diagnosis.append('Moderate Depression Symptoms'); has_significant_issue = True
    elif depression_severity == 'Mild': diagnosis.append('Mild Depression Symptoms')
    else: diagnosis.append('Minimal Depression Symptoms') # Rule 6.1


    # Anxiety (Rules 7-11)
    if anxiety_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Severe': diagnosis.append('Severe Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Moderate': diagnosis.append('Moderate Anxiety Symptoms'); has_significant_issue = True
    elif anxiety_severity == 'Mild': diagnosis.append('Mild Anxiety Symptoms')
    else: diagnosis.append('Minimal Anxiety Symptoms') # Rule 11.1


    # Stress (Rules 12-16)
    if stress_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Severe': diagnosis.append('Severe Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Moderate': diagnosis.append('Moderate Stress Symptoms'); has_significant_issue = True
    elif stress_severity == 'Mild': diagnosis.append('Mild Stress Symptoms')
    else: diagnosis.append('Minimal Stress Symptoms') # Rule 16.1


    # Sleep (Rules 17-21)
    if sleep_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Severe': diagnosis.append('Severe Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Moderate': diagnosis.append('Moderate Sleep Disturbance'); has_significant_issue = True
    elif sleep_severity == 'Mild': diagnosis.append('Mild Sleep Disturbance')
    else: diagnosis.append('Minimal Sleep Disturbance') # Rule 21.1


    # Perceived Stress (Rules 22-26)
    if perceived_stress_severity == 'Extremely Severe': diagnosis.append('Extremely Severe Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Severe': diagnosis.append('Severe Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Moderate': diagnosis.append('Moderate Perceived Stress'); has_significant_issue = True
    elif perceived_stress_severity == 'Mild': diagnosis.append('Mild Perceived Stress')
    else: diagnosis.append('Minimal Perceived Stress') # Rule 26.1


    # --- Rule Set 3: Co-occurrence and Specific Patterns (Rules 27-30.3) ---
    # Rule 27: Mixed Anxiety-Depressive Disorder (Common Co-occurrence)
    if depression_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       anxiety_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Possible Mixed Anxiety-Depressive Symptoms')
        has_significant_issue = True
    # Rule 28: Stress impacting sleep
    if stress_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       sleep_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Stress-induced Sleep Issues')
        has_significant_issue = True
    # Rule 29: Anxiety impacting sleep
    if anxiety_severity in ['Moderate', 'Severe', 'Extremely Severe'] and \
       sleep_severity in ['Moderate', 'Severe', 'Extremely Severe']:
        diagnosis.append('Anxiety-induced Sleep Issues')
        has_significant_issue = True
    # Rule 30: Primary concern: Stress Management if stress is dominant
    if stress_severity in ['Moderate', 'Severe'] and all(get_severity(scores[k]) == 'Minimal' for k in ['depression', 'anxiety', 'sleep'] if k != 'stress'):
        diagnosis.append('Primary concern: Stress Management')
    # Rule 30.1: Primary concern: Sleep Health if sleep is dominant
    if sleep_severity in ['Moderate', 'Severe'] and all(get_severity(scores[k]) == 'Minimal' for k in ['depression', 'anxiety', 'stress'] if k != 'sleep'):
        diagnosis.append('Primary concern: Sleep Health')
    # Rule 30.2: Persistent sadness without other major symptoms
    if depression_severity == 'Moderate' and anxiety_severity == 'Minimal' and stress_severity == 'Minimal':
        diagnosis.append('Primary concern: Persistent Sadness/Low Mood')
    # Rule 30.3: High perceived stress with moderate general symptoms
    if perceived_stress_severity in ['Severe', 'Extremely Severe'] and overall_severity == 'Moderate':
        diagnosis.append('High Perceived Stress Impacting Overall Well-being')




    # --- Rule Set 4: Overall Severity Determination (Rules 31-35.3) ---
    overall_severity = 'Minimal'
    severity_order = ['Minimal', 'Mild', 'Moderate', 'Severe', 'Extremely Severe']
    current_max_index = 0


    for sev in [depression_severity, anxiety_severity, stress_severity, sleep_severity, perceived_stress_severity]:
        index = severity_order.index(sev)
        if index > current_max_index:
            current_max_index = index
    overall_severity = severity_order[current_max_index]


    # Rule 35.1: If no specific diagnosis but some scores are not minimal
    if not has_significant_issue and overall_severity != 'Minimal' and not diagnosis:
        diagnosis.append('General Mild Discomfort')
    # Rule 35.2: If multiple severe symptoms
    if sum(1 for s in [depression_severity, anxiety_severity, stress_severity] if s in ['Severe', 'Extremely Severe']) >= 2:
        diagnosis.append('Complex Presentation with Multiple Severe Symptoms')
        overall_severity = 'Extremely Severe' # Elevate overall severity
    # Rule 35.3: If all major categories are at least moderate
    if all(get_severity(scores[k]) in ['Moderate', 'Severe', 'Extremely Severe'] for k in ['depression', 'anxiety', 'stress']):
        diagnosis.append('Widespread Moderate to Severe Symptoms')
        if overall_severity in ['Mild', 'Moderate']: # Ensure severity is elevated if not already
            overall_severity = 'Severe'


    # --- Rule Set 5: Recommendations based on Overall Severity (Rules 36-50.1) ---


    # Rule 36: General recommendation for any level of concern
    if overall_severity != 'Minimal':
        recommendations.append('It\'s important to take care of your mental well-being.')


    # --- Rule Set 6: Specific Issue Recommendations (Rules 51-70) ---


    # Depression Specific Recommendations (Rules 51-54)
    if depression_severity == 'Mild':
        recommendations.append(["Stay connected : socializing with friends and family.",
                                "Exercise regularly : briskwalking, jogging, or swimming can relax your mind and releases endorphins.",
                                "Mantained a balanced diet : eating nutritious meals can support overall well-being.",
                                "Enough sleep : getting enough rest is important for your mind.",
                                "Practice mindfulness : techniques like meditation or deep breathing can help manage stress.",
                                "Limit caffeine : reducing the intake of caffein can prevent mood fluctuations.",
                                "Engage in enjoyable activites : trying new hobbies can make life worth living again.",
                                "Seek professional support : therapy or counselling can provide guidance tailored to individual needs."])
    elif depression_severity == 'Moderate':
        recommendations.append(["Psychotheraphy : cognitive behavioral therapy helps in managing thought patterns and behaviours.",
                                "Medication (if needed) : antidepressants could help if your symptoms significantly impact daily life.",
                                "Structured routine : mantain a consistent schedule for sleep, meals, and activities can help stabilize mood.",
                                "Exercise : physical activity such as hiking, jogging, or swimming can improve symptoms by boosting endorphins.",
                                "Social support : talk and engage with friends, family, or support groups to relief emotional tentions.",
                                "Relaxation techniques : medication or deep breathing is proven effective in managing stress.",
                                "Professional guidance : consulting a mental health professional ensures tailored treatment."])
    elif depression_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Psychotheraphy : cognitive behavioral therapy (CBT) is highly effective for severe depression.",
                                "Medication : antidepressants may be necessary to help manage symptoms.",
                                "Hospitalization (if needed) : in cases of severe risk to self or others, inpatient care may be required.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Support networks : engage with support groups or community resources for additional help.",
                                "Emergency contacts : have a plan in place for immediate support if suicidal thoughts intensify."])


    # Anxiety Specific Recommendations (Rules 55-58)
    if anxiety_severity == 'Mild':
        recommendations.append(["Regular exercise : physical activity can help regulate stress hormones and boosts mood.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation.",
                                "Healthy lifestyle : maintain a balanced diet, get enough sleep, and limit caffeine intake.",
                                "Journaling : writing down your thoughts can help process feelings and reduce anxiety.",
                                "Gradual exposure : slowly facing feared situations can help desensitize anxiety responses.",
                                "Support network : talk to friends or family about your feelings to gain perspective."])
    elif anxiety_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge anxious thought patterns.",
                                "Medication (if needed) : anti-anxiety medications can help manage symptoms.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep is sufficient to regulate and stabilize hormones.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce anxiety.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Deep brething exercises : techniques like diaphragmatic breathing can help calm the nervous system.",
                                "Journaling : writing about your feelings can help process anxiety and identify triggers."])
    elif anxiety_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Exposure Therapy with a licensed therapist is highly recommended.",
                                "Medication : anti-anxiety medications may be necessary to manage severe symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if anxiety becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe anxiety leading to functional impairment or risk of harm."])


    # Stress Specific Recommendations (Rules 59-62)
    if stress_severity == 'Mild':
        recommendations.append(["Take regular breaks : short breaks during work, study, or using social media can help refresh your mind.",
                                "Practice relaxation techniques : deep breathing, meditation, or yoga can reduce stress levels.",
                                "Time management : prioritize tasks and set realistic goals to avoid feeling overwhelmed.",
                                "Healthy lifestyle : regular exercise, balanced diet, and sufficient sleep are essential for managing stress.",
                                "Social support : talk to friends or family about your stressors to gain perspective and support.",
                                "Engage in enjoyable activities : hobbies or leisure activities can provide a much-needed distraction from stress.",
                                "Practice gratitude : focusing on positive aspects of life can help shift your mindset away from stressors.",
                                "Limit exposure to stressors : identify and reduce sources of stress in your environment, such as negative news or toxic relationships."])
    elif stress_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge unhelpful thought patterns contributing to stress.",
                                "Time management skills : learning to prioritize tasks and set realistic goals can help reduce feelings of being overwhelmed.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce stress.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep are crucial for managing stress.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation."])
    elif stress_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Stress Management Therapy with a licensed therapist is highly recommended.",
                                "Medication (if needed) : anti-anxiety or antidepressant medications may be necessary to manage severe stress symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if stress becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe stress leading to functional impairment or risk of harm."])


    # Sleep Specific Recommendations (Rules 63-66)
    if sleep_severity == 'Mild':
        recommendations.append(["Mantain a consistent sleep schedule : go to bed and wake up at the same time every day, even on weekends.",
                                "Create a relaxing bedtime routine : engage in calming activities before sleep, such as reading or taking a warm bath.",
                                "Limit screen time : avoid screens at least 30 minutes before bed to reduce blue light exposure.",
                                "Create a comfortable sleep environment : ensure your bedroom is dark, quiet, and at a comfortable temperature.",
                                "Avoid stimulants : limit caffeine and nicotine intake, especially in the afternoon and evening.",
                                "Exercise regularly : physical activity during the day can help improve sleep quality, but avoid vigorous exercise close to bedtime.",
                                "Manage stress : practice relaxation techniques like deep breathing or meditation to calm your mind before sleep."])
    elif sleep_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy for Insomnia (CBT-I) : a structured program that helps identify and change thoughts and behaviors that cause or worsen sleep problems.",
                                "Sleep hygiene education : learn about good sleep practices, such as maintaining a consistent sleep schedule and creating a restful environment.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can help reduce anxiety and promote better sleep.",
                                "Limit naps : avoid long daytime naps, especially in the afternoon, to improve nighttime sleep quality.",
                                "Medication (if needed) : short-term use of sleep aids may be considered under medical supervision, but should not be the first line of treatment."])
    elif sleep_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy for Insomnia (CBT-I) with a licensed therapist is highly recommended.",
                                "Medication (if needed) : prescription sleep aids may be necessary to manage severe sleep disturbances, but should be used under medical supervision.",
                                "Sleep studies : in some cases, a sleep study may be needed to diagnose underlying sleep disorders such as sleep apnea.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe insomnia leading to functional impairment or risk of harm."])


    # Perceived Stress Specific Recommendations (Rules 67-70)
    if perceived_stress_severity == 'Mild':
        recommendations.append(["Practice relaxation techniques : deep breathing, meditation, or yoga can help reduce perceived stress levels.",
                                "Time management : prioritize tasks and set realistic goals to avoid feeling overwhelmed.",
                                "Healthy lifestyle : regular exercise, balanced diet, and sufficient sleep are essential for managing perceived stress.",
                                "Social support : talk to friends or family about your stressors to gain perspective and support.",
                                "Engage in enjoyable activities : hobbies or leisure activities can provide a much-needed distraction from stress.",
                                "Practice gratitude : focusing on positive aspects of life can help shift your mindset away from stressors.",
                                "Limit exposure to stressors : identify and reduce sources of stress in your environment, such as negative news or toxic relationships."])
    elif perceived_stress_severity == 'Moderate':
        recommendations.append(["Cognitive Behavioral Therapy (CBT) : helps identify and challenge unhelpful thought patterns contributing to perceived stress.",
                                "Time management skills : learning to prioritize tasks and set realistic goals can help reduce feelings of being overwhelmed.",
                                "Relaxation techniques : practices like progressive muscle relaxation or guided imagery can reduce perceived stress.",
                                "Healthy lifestyle : regular exercise, balanced diet, and quality sleep are crucial for managing perceived stress.",
                                "Stress management skills : learning to identify and cope with stressors can be beneficial.",
                                "Professional support : consider therapy or counseling for personalized strategies.",
                                "Mindfulness practices : meditation, yoga, or deep breathing exercises can promote relaxation."])
    elif perceived_stress_severity in ['Severe', 'Extremely Severe']:
        recommendations.append(["Intensive therapy : Cognitive Behavioral Therapy (CBT) or Stress Management Therapy with a licensed therapist is highly recommended.",
                                "Medication (if needed) : anti-anxiety or antidepressant medications may be necessary to manage severe perceived stress symptoms.",
                                "Support groups : connecting with others who experience similar issues can provide comfort and understanding.",
                                "Emergency contacts : have a plan for immediate support if perceived stress becomes overwhelming.",
                                "Regular follow-ups : consistent check-ins with a mental health professional are crucial for monitoring progress.",
                                "Lifestyle adjustments : maintain a healthy diet, regular exercise, and sufficient sleep to support overall mental health.",
                                "Hospitalization or crisis care : may be required in cases of severe perceived stress leading to functional impairment or risk of harm."])


    # Holistic well-being (Rule 71)
    if overall_severity != 'Minimal':
        recommendations.append('Remember that mental health is as important as physical health. Be kind to yourself and seek support when needed. Prioritize self-care and open communication with trusted individuals.')
   
    # If only minimal symptoms across the board (Rule 72)
    if overall_severity == 'Minimal' and not has_significant_issue and not diagnosis:
        recommendations.append('Continue to monitor your well-being. Maintaining a healthy lifestyle, including regular exercise, balanced nutrition, and sufficient sleep, is key for mental resilience. Pay attention to early signs of stress or low mood.')




    # --- Rule Set 7: Contraindication and Malaysia-Specific Resources (Rules 73-77) ---
    # Rule 73: Contraindication rule (medical conditions)
    if scores['medical_condition']:
        recommendations.insert(0, '**Important Note:** Given your mention of a medical condition/medication, it is crucial to consult with your primary care physician or a specialist first. They can help determine if your symptoms are related to your physical health or medication, and ensure any mental health recommendations are safe and appropriate for your overall health. Always discuss mental health concerns with them.')


    # Rule 74: General Malaysia Hotlines (Always include if not Minimal)
    if overall_severity != 'Minimal':
        recommendations.append('\n**Malaysia Mental Health Hotlines:**')
        for hotline in MALAYSIA_RESOURCES['hotlines']:
            line_info = f"- {hotline['name']}: "
            if "number" in hotline:
                line_info += f"{hotline['number']}"
                if "hours" in hotline:
                    line_info += f" ({hotline['hours']})"
            if "whatsapp" in hotline:
                line_info += f" (WhatsApp: {hotline['whatsapp']})"
            if "website" in hotline:
                line_info += f" [Website]({hotline['website']})"
            recommendations.append(line_info)


    # Rule 75: Guidance on finding therapists in Malaysia (Always include if not Minimal)
    if overall_severity != 'Minimal':
        recommendations.append('\n**Finding a Therapist in Malaysia:**')
        for guidance in MALAYSIA_RESOURCES['therapist_guidance']:
            recommendations.append(f"- {guidance}")


    # Rule 76: Encourage follow-up
    recommendations.append('\n')
    recommendations.append('This system provides general guidance. For a comprehensive assessment and personalized treatment plan, always consult with a qualified mental health professional.')
    # Rule 77: Disclaimer for automated system
    recommendations.append('Remember, PsychQuick is an automated system and not a substitute for professional medical or psychological advice. It is designed to provide preliminary insights and connect you with resources.')
    # Rule 78: Encourage open communication
    recommendations.append('Don\'t hesitate to talk to someone you trust about how you\'re feeling. Sharing your experiences can be a powerful first step towards healing.')


    return diagnosis, overall_severity, recommendations


# Helper to format the final response for the frontend
def format_response_for_frontend(diagnosis, overall_severity, recommendations):
    response_text = ""
    if diagnosis:
        # Filter out "Minimal" symptoms from the diagnosis list to keep it concise and focused
        filtered_diagnosis = [d for d in diagnosis if not d.startswith('Minimal')]
        if filtered_diagnosis:
            response_text += f"**Potential Areas of Concern:** {', '.join(filtered_diagnosis)}\n\n"
        else:
            response_text += "**No significant concerns identified based on the provided symptoms.**\n\n"
    else:
        response_text += "**No significant concerns identified based on the provided symptoms.**\n\n"


    response_text += f"**Overall Severity:** {overall_severity}\n\n"
    response_text += "**Recommendations:**\n"
    for rec in recommendations:
        response_text += f"- {rec}\n"
    return response_text


# --- Flask Routes ---


@app.route('/')
def index():
    """Renders the main chat interface and initializes session."""
    # Reset session on fresh page load to start a new conversation
    session.clear()
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '').strip()
    exit_keywords = ['stop', 'quit', 'end', 'exit', "that's all", 'no more']
    if any(word in user_input.lower() for word in exit_keywords):
        chat_state = session.get('chat_state')
        if chat_state:
            scores = chat_state.get('symptom_scores', {})
            diagnosis, overall_severity, recommendations = apply_rules(scores)
            session.clear()
            final_response = format_response_for_frontend(diagnosis, overall_severity, recommendations)
            final_response += "\n\n_You chose to end the chat. Thank you for using PsychQuick._ 💙"
            return jsonify({"response": final_response})
        else:
            return jsonify({"response": "Session ended. Thank you for using PsychQuick. 💙"})

   
    # Initialize session state if it's a new conversation or session cleared
    if 'chat_state' not in session or not session['chat_state']:
        session['chat_state'] = {
            'current_stage': 'awaiting_first_symptomatic_input', # Initial state on first interaction
            'symptom_scores': {
                'depression': 0, 'anxiety': 0, 'stress': 0,
                'sleep': 0, 'perceived_stress': 0,
                'medical_condition': False, 'suicidal_thoughts': False,
            },
            'question_indices': { # Track current question index for each category
                'depression': 0, 'anxiety': 0, 'stress': 0,
                'sleep': 0, 'perceived_stress': 0, 'medical_condition': 0
            },
            'last_asked_category': None, # Track the last symptom category a question was asked from
            'last_question_suicidal_ideation': False, # Flag if the last question asked was the suicidal ideation prompt
        }


    chat_state = session['chat_state']


    # Process user input and update scores
    if user_input:
        new_scores = analyze_symptoms(user_input)
        chat_state['symptom_scores'] = update_session_scores(chat_state['symptom_scores'], new_scores)
        session.modified = True # Mark session as modified


    # Determine next action (question or diagnosis)
    response_text = get_next_question_or_diagnosis(chat_state, user_input)


    # Simulate processing time
    time.sleep(1.0)


    return jsonify({"response": response_text})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
