"""
Database seeding script — creates demo data for EduScale.

Run: python -m app.seed.seed_database
All data is clearly fictional demo data.
"""
import uuid
import random
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.database import SessionLocal, engine, Base
from app.models import *
from app.services.auth_service import hash_password


def seed():
    """Seed the database with demo data."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).first():
            print("Database already seeded. Skipping.")
            return

        print("🌱 Seeding EduScale database...")

        # ── Users ──
        teacher_user = User(
            email="teacher@eduscale.demo",
            password_hash=hash_password("teacher123"),
            full_name="Dr. Sarah Mitchell",
            role=UserRole.TEACHER,
            avatar_url="/avatars/teacher_1.svg",
        )
        db.add(teacher_user)
        db.flush()

        student_data = [
            ("Alex Johnson", "alex@eduscale.demo", "/avatars/student_1.svg"),
            ("Priya Sharma", "priya@eduscale.demo", "/avatars/student_2.svg"),
            ("Marcus Chen", "marcus@eduscale.demo", "/avatars/student_3.svg"),
            ("Sofia Rodriguez", "sofia@eduscale.demo", "/avatars/student_4.svg"),
            ("James Okafor", "james@eduscale.demo", "/avatars/student_5.svg"),
            ("Emma Wilson", "emma@eduscale.demo", "/avatars/student_6.svg"),
            ("Ravi Patel", "ravi@eduscale.demo", "/avatars/student_7.svg"),
            ("Lina Kim", "lina@eduscale.demo", "/avatars/student_8.svg"),
        ]

        student_users = []
        for name, email, avatar in student_data:
            u = User(
                email=email,
                password_hash=hash_password("student123"),
                full_name=name,
                role=UserRole.STUDENT,
                avatar_url=avatar,
            )
            db.add(u)
            student_users.append(u)
        db.flush()

        # ── Teacher profile ──
        teacher = Teacher(
            user_id=teacher_user.id,
            teacher_code="TCH-001",
            department="Computer Science",
        )
        db.add(teacher)
        db.flush()

        # ── Student profiles ──
        students = []
        for i, u in enumerate(student_users):
            s = Student(
                user_id=u.id,
                student_code=f"STU-{i+1:03d}",
                grade_level=1,
            )
            db.add(s)
            students.append(s)
        db.flush()

        # ── Course ──
        course = Course(
            name="Introduction to Python Programming",
            code="CS101",
            description="A beginner-friendly course covering Python fundamentals including variables, control flow, functions, data structures, and object-oriented programming.",
            difficulty_level="beginner",
        )
        db.add(course)
        db.flush()

        # ── Topics ──
        topic_names = [
            ("Python Basics", "Variables, data types, operators, and basic I/O"),
            ("Control Flow", "If/else statements, conditional logic, and boolean expressions"),
            ("Loops", "For loops, while loops, loop control statements"),
            ("Functions", "Function definition, parameters, return values, scope"),
            ("Lists & Tuples", "List operations, slicing, tuple immutability"),
            ("Dictionaries & Sets", "Key-value pairs, set operations, dictionary methods"),
            ("Strings", "String methods, formatting, regular expressions basics"),
            ("File Handling", "Reading and writing files, context managers"),
            ("Error Handling", "Try/except, custom exceptions, debugging"),
            ("OOP Basics", "Classes, objects, inheritance, polymorphism"),
        ]

        topics = []
        for i, (name, desc) in enumerate(topic_names):
            t = Topic(course_id=course.id, name=name, description=desc, order_index=i)
            db.add(t)
            topics.append(t)
        db.flush()

        # ── Classes ──
        class_a = Class(
            teacher_id=teacher.id, course_id=course.id,
            name="Class A", section="A", academic_year="2024-25",
        )
        class_b = Class(
            teacher_id=teacher.id, course_id=course.id,
            name="Class B", section="B", academic_year="2024-25",
        )
        db.add_all([class_a, class_b])
        db.flush()

        # Enroll students
        for i, s in enumerate(students):
            cls = class_a if i < 5 else class_b
            db.add(Enrollment(student_id=s.id, class_id=cls.id))
        db.flush()

        # ── Questions ──
        questions_by_topic = _create_questions(db, course, topics)

        # ── Quizzes ──
        quizzes = _create_quizzes(db, course, topics, questions_by_topic)

        # ── Demo quiz attempts & mastery ──
        rng = random.Random(42)
        for student in students:
            _create_student_attempts(db, student, quizzes, topics, questions_by_topic, rng)
        db.flush()

        # ── Notes ──
        _create_notes(db, course, topics)

        # ── Assignments ──
        _create_assignments(db, teacher, students, topics, rng)

        # ── Notifications ──
        _create_notifications(db, students, rng)

        db.commit()
        print("✅ Database seeded successfully!")
        print(f"   Teacher: teacher@eduscale.demo / teacher123")
        print(f"   Students: alex@eduscale.demo / student123 (and 7 more)")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


def _create_questions(db, course, topics):
    """Create question bank for all topics."""
    questions_by_topic = {}

    all_questions = {
        "Python Basics": [
            ("What is the output of: print(type(42))?", {"A": "<class 'int'>", "B": "<class 'str'>", "C": "<class 'float'>", "D": "<class 'number'>"}, "A", "In Python, 42 is an integer literal, so type() returns <class 'int'>.", "beginner"),
            ("Which operator is used for exponentiation in Python?", {"A": "^", "B": "**", "C": "//", "D": "%%"}, "B", "The ** operator is used for exponentiation. For example, 2**3 = 8.", "beginner"),
            ("What is the result of 10 // 3?", {"A": "3.33", "B": "3", "C": "4", "D": "3.0"}, "B", "// is the floor division operator. 10 // 3 = 3 (integer division).", "beginner"),
            ("Which of the following is a valid variable name?", {"A": "2name", "B": "my-var", "C": "_count", "D": "class"}, "C", "_count is valid. Variable names can start with _ or letter, not digit. 'class' is a reserved keyword.", "beginner"),
            ("What does the input() function return?", {"A": "int", "B": "float", "C": "str", "D": "depends on input"}, "C", "input() always returns a string. You must explicitly convert it to other types.", "intermediate"),
        ],
        "Control Flow": [
            ("What is the output of: print(5 > 3 and 2 < 1)?", {"A": "True", "B": "False", "C": "Error", "D": "None"}, "B", "5>3 is True but 2<1 is False. True and False = False.", "beginner"),
            ("Which keyword is used for else-if in Python?", {"A": "else if", "B": "elseif", "C": "elif", "D": "elsif"}, "C", "Python uses 'elif' as the else-if keyword.", "beginner"),
            ("What does 'pass' do in an if block?", {"A": "Skips the condition", "B": "Does nothing (placeholder)", "C": "Exits the program", "D": "Returns None"}, "B", "'pass' is a null operation — a placeholder when a statement is syntactically required.", "beginner"),
            ("What is the output of: print(not False)?", {"A": "True", "B": "False", "C": "Error", "D": "not False"}, "A", "'not' negates a boolean. not False = True.", "beginner"),
            ("What is short-circuit evaluation?", {"A": "Evaluating all conditions", "B": "Skipping remaining conditions once result is determined", "C": "An error type", "D": "A loop optimization"}, "B", "Short-circuit: Python stops evaluating 'and'/'or' once the result is known.", "intermediate"),
        ],
        "Loops": [
            ("How many times does 'for i in range(5)' iterate?", {"A": "4", "B": "5", "C": "6", "D": "Error"}, "B", "range(5) produces [0,1,2,3,4] — 5 iterations.", "beginner"),
            ("Which statement immediately exits a loop?", {"A": "continue", "B": "pass", "C": "break", "D": "exit"}, "C", "'break' exits the loop immediately.", "beginner"),
            ("What does 'continue' do in a loop?", {"A": "Exits loop", "B": "Skips to next iteration", "C": "Pauses loop", "D": "Restarts loop"}, "B", "'continue' skips the rest of the current iteration and moves to the next.", "beginner"),
            ("What is the output of: list(range(2, 10, 3))?", {"A": "[2, 5, 8]", "B": "[2, 4, 6, 8]", "C": "[3, 6, 9]", "D": "[2, 5, 8, 11]"}, "A", "range(2, 10, 3) starts at 2, steps by 3: 2, 5, 8.", "intermediate"),
            ("What is a nested loop?", {"A": "A loop inside a function", "B": "A loop inside another loop", "C": "Two sequential loops", "D": "A recursive loop"}, "B", "A nested loop is a loop placed inside the body of another loop.", "beginner"),
        ],
        "Functions": [
            ("How do you define a function in Python?", {"A": "function myFunc():", "B": "def myFunc():", "C": "func myFunc():", "D": "define myFunc():"}, "B", "Python uses 'def' keyword to define functions.", "beginner"),
            ("What is the default return value of a function?", {"A": "0", "B": "''", "C": "None", "D": "False"}, "C", "If a function has no return statement, it returns None.", "beginner"),
            ("What is a lambda function?", {"A": "A named function", "B": "An anonymous inline function", "C": "A recursive function", "D": "A class method"}, "B", "Lambda is a small anonymous function: lambda x: x+1.", "intermediate"),
            ("What does *args do in a function?", {"A": "Makes arguments optional", "B": "Accepts variable positional arguments as a tuple", "C": "Multiplies arguments", "D": "Creates a list"}, "B", "*args collects extra positional arguments into a tuple.", "intermediate"),
            ("What is variable scope?", {"A": "Variable data type", "B": "Where a variable can be accessed", "C": "Variable memory size", "D": "Variable name length"}, "B", "Scope determines where in the code a variable can be referenced.", "beginner"),
        ],
        "Lists & Tuples": [
            ("How do you create an empty list?", {"A": "list = ()", "B": "list = []", "C": "list = {}", "D": "list = <>"}, "B", "Empty list: [] or list(). () is a tuple, {} is a dict.", "beginner"),
            ("What does list.append(x) do?", {"A": "Adds x at beginning", "B": "Adds x at end", "C": "Removes x", "D": "Sorts the list"}, "B", "append() adds an element to the end of the list.", "beginner"),
            ("What is the output of: [1,2,3][1:3]?", {"A": "[1, 2]", "B": "[2, 3]", "C": "[1, 2, 3]", "D": "[2]"}, "B", "Slicing [1:3] returns elements at index 1 and 2: [2, 3].", "beginner"),
            ("Can you modify a tuple after creation?", {"A": "Yes", "B": "No", "C": "Only if it contains lists", "D": "Only the first element"}, "B", "Tuples are immutable. You cannot change their elements after creation.", "beginner"),
            ("What does list comprehension do?", {"A": "Sorts a list", "B": "Creates a new list using a compact expression", "C": "Deletes list items", "D": "Counts list items"}, "B", "List comprehension: [x**2 for x in range(5)] creates a new list.", "intermediate"),
        ],
        "Dictionaries & Sets": [
            ("How do you access value for key 'name' in dict d?", {"A": "d.name", "B": "d['name']", "C": "d(name)", "D": "d.get[name]"}, "B", "Use d['name'] or d.get('name') to access dictionary values.", "beginner"),
            ("What happens if you access a non-existent key with d['key']?", {"A": "Returns None", "B": "Returns 0", "C": "Raises KeyError", "D": "Returns empty string"}, "C", "Accessing a missing key with [] raises KeyError. Use .get() for a safe default.", "beginner"),
            ("What is the main property of a set?", {"A": "Ordered elements", "B": "Unique elements", "C": "Key-value pairs", "D": "Fixed size"}, "B", "Sets contain only unique elements. Duplicates are automatically removed.", "beginner"),
            ("How do you merge two dictionaries in Python 3.9+?", {"A": "d1 + d2", "B": "d1 | d2", "C": "d1 & d2", "D": "merge(d1, d2)"}, "B", "Python 3.9+ supports dict merging with |: d1 | d2.", "intermediate"),
            ("Which method removes and returns a key-value pair?", {"A": "del()", "B": "remove()", "C": "pop()", "D": "discard()"}, "C", "dict.pop(key) removes the key and returns its value.", "intermediate"),
        ],
        "Strings": [
            ("What does 'hello'.upper() return?", {"A": "'Hello'", "B": "'HELLO'", "C": "'hello'", "D": "Error"}, "B", ".upper() converts all characters to uppercase.", "beginner"),
            ("How do you check if a string contains a substring?", {"A": "str.has('sub')", "B": "'sub' in str", "C": "str.contains('sub')", "D": "str.find('sub')"}, "B", "Use the 'in' operator: 'sub' in mystring returns True/False.", "beginner"),
            ("What is an f-string?", {"A": "A file string", "B": "A formatted string literal", "C": "A frozen string", "D": "A function string"}, "B", "f-strings (f'Hello {name}') allow inline expression evaluation.", "beginner"),
            ("What does 'abc'.join(['1','2','3']) return?", {"A": "'1abc2abc3'", "B": "'abc123'", "C": "'123abc'", "D": "'1,2,3'"}, "A", "join() inserts the string between each element: '1abc2abc3'.", "intermediate"),
            ("Are Python strings mutable?", {"A": "Yes", "B": "No", "C": "Only with special methods", "D": "Depends on length"}, "B", "Strings are immutable. Operations like upper() return new strings.", "beginner"),
        ],
        "File Handling": [
            ("Which function opens a file in Python?", {"A": "file()", "B": "open()", "C": "read()", "D": "load()"}, "B", "open() is used to open files. Always close files or use 'with' statement.", "beginner"),
            ("What mode opens a file for writing (overwrite)?", {"A": "'r'", "B": "'w'", "C": "'a'", "D": "'x'"}, "B", "'w' mode opens for writing, creating or truncating the file.", "beginner"),
            ("What is the advantage of 'with open()' syntax?", {"A": "Faster I/O", "B": "Automatic file closing", "C": "Better formatting", "D": "Compression"}, "B", "'with' is a context manager that automatically closes the file.", "beginner"),
            ("What does 'a' mode do?", {"A": "Opens for reading", "B": "Opens for appending", "C": "Opens for writing (overwrite)", "D": "Auto-detect"}, "B", "'a' mode opens for appending — writes go to the end of the file.", "beginner"),
            ("How do you read all lines into a list?", {"A": "f.read()", "B": "f.readlines()", "C": "f.readline()", "D": "f.lines()"}, "B", "readlines() returns a list of all lines. read() returns a single string.", "intermediate"),
        ],
        "Error Handling": [
            ("Which keyword starts exception handling?", {"A": "catch", "B": "try", "C": "handle", "D": "error"}, "B", "Python uses try/except for exception handling.", "beginner"),
            ("What exception is raised for division by zero?", {"A": "ValueError", "B": "TypeError", "C": "ZeroDivisionError", "D": "MathError"}, "C", "Division by zero raises ZeroDivisionError.", "beginner"),
            ("What does 'finally' block do?", {"A": "Handles errors", "B": "Always executes after try/except", "C": "Stops the program", "D": "Retries the operation"}, "B", "'finally' block runs whether or not an exception occurred.", "beginner"),
            ("How do you raise a custom exception?", {"A": "throw Error()", "B": "raise Exception('msg')", "C": "error('msg')", "D": "new Exception('msg')"}, "B", "Use raise keyword: raise ValueError('invalid input').", "intermediate"),
            ("What is the purpose of 'except Exception as e'?", {"A": "Create a new exception", "B": "Catch exception and store it in variable e", "C": "Log the exception", "D": "Ignore the exception"}, "B", "'as e' captures the exception object for inspection.", "beginner"),
        ],
        "OOP Basics": [
            ("How do you define a class in Python?", {"A": "class MyClass:", "B": "def MyClass:", "C": "create MyClass:", "D": "type MyClass:"}, "A", "Use 'class' keyword followed by class name and colon.", "beginner"),
            ("What is __init__ in a class?", {"A": "A destructor", "B": "The constructor/initializer", "C": "A private method", "D": "A static method"}, "B", "__init__ is the constructor — called when an object is created.", "beginner"),
            ("What does 'self' refer to?", {"A": "The class itself", "B": "The current instance", "C": "The parent class", "D": "A global variable"}, "B", "'self' refers to the current instance of the class.", "beginner"),
            ("What is inheritance?", {"A": "Copying a class", "B": "A class deriving from another class", "C": "Deleting a class", "D": "Renaming a class"}, "B", "Inheritance allows a class to inherit attributes and methods from another.", "intermediate"),
            ("What is polymorphism?", {"A": "Multiple constructors", "B": "Same interface, different implementations", "C": "Private methods", "D": "Static typing"}, "B", "Polymorphism: different classes can implement the same method differently.", "intermediate"),
        ],
    }

    for topic in topics:
        q_list = all_questions.get(topic.name, [])
        questions_by_topic[topic.id] = []
        for q_text, options, answer, explanation, diff in q_list:
            q = Question(
                course_id=course.id, topic_id=topic.id,
                question_type=QuestionType.MULTIPLE_CHOICE,
                difficulty=DifficultyLevel(diff),
                question_text=q_text,
                options=options, correct_answer=answer,
                explanation=explanation,
            )
            db.add(q)
            questions_by_topic[topic.id].append(q)
    db.flush()
    return questions_by_topic


def _create_quizzes(db, course, topics, questions_by_topic):
    """Create quizzes from the question bank."""
    quizzes = []
    for topic in topics:
        q_list = questions_by_topic.get(topic.id, [])
        if not q_list:
            continue
        quiz = Quiz(
            course_id=course.id, topic_id=topic.id,
            title=f"Quiz: {topic.name}",
            description=f"Test your knowledge of {topic.name}",
            difficulty="beginner", question_count=len(q_list),
            time_limit_minutes=15,
        )
        db.add(quiz)
        db.flush()
        for i, q in enumerate(q_list):
            db.add(QuizQuestion(quiz_id=quiz.id, question_id=q.id, order_index=i))
        quizzes.append(quiz)
    db.flush()
    return quizzes


def _create_student_attempts(db, student, quizzes, topics, questions_by_topic, rng):
    """Generate realistic demo quiz attempts and mastery."""
    # Each student attempts a random subset of quizzes with varying performance
    student_strength = rng.uniform(0.3, 0.95)

    for quiz in quizzes:
        if rng.random() < 0.3:  # Skip some quizzes
            continue

        qq_items = [qq for qq in db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).all()]
        if not qq_items:
            continue

        attempt = QuizAttempt(
            student_id=student.id, quiz_id=quiz.id,
            status="completed",
            started_at=datetime.utcnow() - timedelta(days=rng.randint(1, 30)),
        )
        attempt.completed_at = attempt.started_at + timedelta(minutes=rng.randint(5, 15))
        db.add(attempt)
        db.flush()

        correct = 0
        total = 0
        for qq in qq_items:
            q = db.query(Question).filter(Question.id == qq.question_id).first()
            if not q:
                continue
            is_correct = rng.random() < student_strength
            answer = q.correct_answer if is_correct else "X"
            if is_correct:
                correct += 1
            total += 1
            resp = StudentResponse(
                attempt_id=attempt.id, question_id=q.id,
                submitted_answer=answer, is_correct=is_correct,
                time_spent_seconds=rng.randint(10, 120),
            )
            db.add(resp)

        attempt.total_questions = total
        attempt.correct_answers = correct
        attempt.score = (correct / total * 100) if total > 0 else 0

    db.flush()

    # Create mastery records
    for topic in topics:
        q_ids = [q.id for q in questions_by_topic.get(topic.id, [])]
        if not q_ids:
            continue

        responses = db.query(StudentResponse).join(QuizAttempt).filter(
            QuizAttempt.student_id == student.id,
            StudentResponse.question_id.in_(q_ids),
        ).all()

        if not responses:
            continue

        total = len(responses)
        correct = sum(1 for r in responses if r.is_correct)
        score = correct / total if total > 0 else 0

        mastery = Mastery(
            student_id=student.id, topic_id=topic.id,
            mastery_score=score,
            questions_attempted=total, questions_correct=correct,
            source="heuristic",
        )
        db.add(mastery)
    db.flush()


def _create_notes(db, course, topics):
    """Create curated educational notes for each topic."""
    notes_content = {
        "Python Basics": {
            "title": "Python Basics — Essential Concepts",
            "summary": "Core Python concepts: variables, data types, operators, and I/O",
            "content": {
                "definitions": [
                    "Variable: A named container for storing data values",
                    "Data Type: The classification of data (int, float, str, bool)",
                    "Operator: A symbol that performs operations on values (+, -, *, /)",
                ],
                "key_concepts": [
                    "Python is dynamically typed — you don't declare variable types",
                    "Variables are created when you first assign a value",
                    "Python supports multiple assignment: a, b = 1, 2",
                    "Use type() to check the data type of a value",
                ],
                "examples": [
                    {
                        "code": "name = 'Alex'\nage = 20\nheight = 5.9\nis_student = True\nprint(f'{name} is {age} years old')",
                        "output": "Alex is 20 years old",
                        "explanation": "Variables store different data types. f-strings embed variables in strings.",
                    }
                ],
                "common_mistakes": [
                    "Using reserved keywords as variable names (class, if, for)",
                    "Starting variable names with numbers",
                    "Confusing = (assignment) with == (comparison)",
                ],
                "revision_checklist": [
                    "Can you name 4 basic data types?",
                    "Do you know the difference between / and //?",
                    "Can you use type() and input()?",
                ],
            },
        },
        "Functions": {
            "title": "Functions — Building Reusable Code",
            "summary": "Function definition, parameters, return values, and scope",
            "content": {
                "definitions": [
                    "Function: A reusable block of code that performs a specific task",
                    "Parameter: A variable in a function definition",
                    "Argument: The actual value passed to a function",
                    "Return Value: The result a function sends back to the caller",
                ],
                "key_concepts": [
                    "Functions are defined with the 'def' keyword",
                    "Functions can have default parameter values",
                    "*args collects extra positional arguments as a tuple",
                    "**kwargs collects extra keyword arguments as a dictionary",
                    "Variables inside functions have local scope",
                ],
                "examples": [
                    {
                        "code": "def greet(name, greeting='Hello'):\n    return f'{greeting}, {name}!'\n\nprint(greet('Alex'))\nprint(greet('Priya', 'Hi'))",
                        "output": "Hello, Alex!\nHi, Priya!",
                        "explanation": "Default parameters provide fallback values. Return sends back results.",
                    }
                ],
                "common_mistakes": [
                    "Forgetting the return statement (function returns None)",
                    "Using mutable default arguments (like lists)",
                    "Confusing local and global variable scope",
                ],
                "revision_checklist": [
                    "Can you write a function with default parameters?",
                    "Do you understand *args and **kwargs?",
                    "Can you explain variable scope?",
                ],
            },
        },
        "Loops": {
            "title": "Loops — Repeating Actions Efficiently",
            "summary": "For loops, while loops, and loop control statements",
            "content": {
                "definitions": [
                    "For Loop: Iterates over a sequence (list, range, string)",
                    "While Loop: Repeats while a condition is True",
                    "break: Exits the loop immediately",
                    "continue: Skips to the next iteration",
                ],
                "key_concepts": [
                    "range(start, stop, step) generates a sequence of numbers",
                    "For loops are preferred when you know the number of iterations",
                    "While loops are for unknown iteration counts",
                    "Nested loops multiply iterations — be careful with performance",
                ],
                "examples": [
                    {
                        "code": "# Print even numbers from 0-10\nfor i in range(0, 11, 2):\n    print(i, end=' ')",
                        "output": "0 2 4 6 8 10",
                        "explanation": "range(0, 11, 2) starts at 0, ends before 11, steps by 2.",
                    }
                ],
                "common_mistakes": [
                    "Infinite while loops (forgetting to update the condition)",
                    "Off-by-one errors with range()",
                    "Modifying a list while iterating over it",
                ],
                "revision_checklist": [
                    "Can you convert a for loop to a while loop?",
                    "Do you know when to use break vs continue?",
                    "Can you write a nested loop?",
                ],
            },
        },
    }

    # Create notes for topics that have content, use generic for others
    for topic in topics:
        if topic.name in notes_content:
            data = notes_content[topic.name]
        else:
            data = {
                "title": f"{topic.name} — Key Concepts",
                "summary": f"Essential concepts and examples for {topic.name}",
                "content": {
                    "definitions": [f"Key concept in {topic.name}"],
                    "key_concepts": [
                        f"Understanding {topic.name} is essential for Python development",
                        f"Practice with examples to solidify {topic.name} concepts",
                    ],
                    "examples": [{"code": f"# Example for {topic.name}\nprint('Practice!')", "output": "Practice!", "explanation": f"A basic example of {topic.name}."}],
                    "common_mistakes": [f"Common pitfall in {topic.name}"],
                    "revision_checklist": [f"Review all {topic.name} concepts"],
                },
            }
        note = Note(
            course_id=course.id, topic_id=topic.id,
            title=data["title"], summary=data["summary"],
            content=data["content"],
            is_ai_generated=False, content_source="curated",
        )
        db.add(note)
    db.flush()


def _create_assignments(db, teacher, students, topics, rng):
    """Create demo assignments."""
    for student in students[:4]:
        weak_topics = [topics[rng.randint(0, len(topics)-1)] for _ in range(2)]
        for topic in weak_topics:
            a = Assignment(
                teacher_id=teacher.id,
                student_id=student.id,
                topic_id=topic.id,
                title=f"Practice: {topic.name}",
                description=f"Additional practice to improve your understanding of {topic.name}",
                difficulty="beginner",
                question_count=5,
                due_date=datetime.utcnow() + timedelta(days=rng.randint(3, 14)),
                status=AssignmentStatus.PENDING,
            )
            db.add(a)
    db.flush()


def _create_notifications(db, students, rng):
    """Create demo notifications."""
    msgs = [
        (NotificationType.RECOMMENDATION, "Study Recommendation", "Based on your recent quiz, we recommend reviewing Python Functions."),
        (NotificationType.ACHIEVEMENT, "Achievement Unlocked!", "You've mastered Python Basics! Great job!"),
        (NotificationType.ASSIGNMENT, "New Assignment", "Your teacher has assigned a new practice test on Loops."),
        (NotificationType.SYSTEM, "Welcome to EduScale!", "Start your learning journey by taking a quiz."),
    ]
    for student in students:
        for n_type, title, msg in msgs:
            if rng.random() < 0.6:
                db.add(Notification(
                    student_id=student.id, type=n_type,
                    title=title, message=msg,
                    is_read=rng.random() < 0.3,
                ))
    db.flush()


if __name__ == "__main__":
    seed()
