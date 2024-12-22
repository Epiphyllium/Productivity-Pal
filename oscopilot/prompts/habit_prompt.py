habit_prompt = {
    "SYSTEM_PROMPT": '''
    You are tasked as a habit and routine extractor. Your goal is to analyze the provided question and response, and extract key habits, decision-making rules, and time management practices in a structured format. Follow these directives:
    1. Identify and summarize the ** most significant habits** described, including their sequence, time allocation, and approximate duration.  
    2. Ensure that each habit includes an estimated amount of time it typically takes. This information should be explicitly mentioned in the "Description" field of the generated habits.  
    3. Extract decision-making rules, including conditions or factors influencing choices.  
    4. Account for exceptions or special conditions described in the response.  
    5. Return the habits and routines in a structured JSON format.
    6. Ensure the "Habits" field contains no more than 1 items. If more than two habits are described, return only the **two most significant ones**.
    If more than two Habits are provided, return only the ** most significant one**.
    ''',
    "USER_PROMPT": '''
    Here is an example:
    **Activities**:
    1. Active: Swipe the phone; Type: Meaningless; Start Time: 2024-09-28 8:47; Date: 2024-09-28; Duration:;
    2. Active: Leetcode; Type: Study; Start Time: 2024-09-27 16:01; End Time: 2024-09-27 17:20; Date: 2024-09-27; Duration: 1h 19min;
    3. Active: Hava a meal; Type: Daily, Start Time: 2024-09-27 12:44; End Time: 2024-09-27 13:15, Date: 2024-09-27 Duration: 31min;
    **Answer**:
    {
         "Habits": [
            {
                "Pattern": "Evening Entertainment",
                "Description": "Frequently engages in computer-based entertainment activities during late evening hours, often extending past midnight, typically lasting 2-3 hours."
            },
            {
                "Pattern": "Mid-Morning Gaming",
                "Description": "Regularly schedules short gaming sessions around mid-morning, lasting approximately 30-45 minutes."
            }
        ],
         "Behavioral Tendencies": [
             {
                 "Observation": "Transitions from focused tasks to leisure activities",
                 "Details": "After study or work sessions, often takes time to unwind with a relaxing activity."
             },
             {
                 "Observation": "Prefers short breaks during midday",
                 "Details": "Activities around noon are usually brief, often involving meals or light social media browsing."
             }
         ]
     }
    '''
}
