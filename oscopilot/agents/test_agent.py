import unittest
from oscopilot.agents.task_schedule_agent import TaskScheduleAgent

class TestAgent(unittest.TestCase):
    def test_agent(self):
        agent=TaskScheduleAgent()
        task_name = "Code Review"
        task_description = "Prepare a code review for NLP." 
        agent.schedule_task(2,task_name,task_description,"2024-11-30 23:59:59")
        

if __name__ == "__main__":
    unittest.main()
    