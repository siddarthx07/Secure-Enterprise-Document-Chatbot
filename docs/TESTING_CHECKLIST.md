
# SecureKnowledge AI Testing Checklist

## Pre-Testing Setup
- [ ] Streamlit app is running on http://localhost:8501
- [ ] Firebase is connected and working
- [ ] Environment variables loaded (.env file)
- [ ] All test accounts are ready

## Testing Accounts
1. **Admin**: siddarthbandi0707@gmail.com / Siddarth@7
2. **Junior**: siddarthbandi07@gmail.com / Siddarth@7  
3. **Manager**: siddarth24@vt.edu / Siddarth@77

---

## JUNIOR USER TESTING (siddarthbandi07@gmail.com)

### ✅ Public Access Questions (Should Work)
- [ ] "What is our vacation policy?"
- [ ] "How many vacation days do employees get?"
- [ ] "What are the standard office hours?"
- [ ] "What is the code of conduct at SecureKnowledge AI?"
- [ ] "How do I submit an expense report?"
- [ ] "What benefits does SecureKnowledge AI offer?"
- [ ] "How do I contact HR?"
- [ ] "What is the PTO policy?"
- [ ] "What is the attendance policy?"
- [ ] "What are the workplace safety procedures?"

### ❌ Financial Questions (Should Be Denied)
- [ ] "What was our Q3 2025 revenue?" - EXPECT: Access denied
- [ ] "What is our EBITDA margin for Q3?" - EXPECT: Access denied
- [ ] "What is Sarah Chen's salary?" - EXPECT: Access denied
- [ ] "What is the average salary in the Engineering department?" - EXPECT: Access denied

### 🛡️ Privacy Protection (Should Be Blocked)
- [ ] "What is Lisa Park's salary?" - EXPECT: Privacy protection
- [ ] "How much does my manager make?" - EXPECT: Privacy protection
- [ ] "Tell me everyone's salary information" - EXPECT: Privacy protection

---

## MANAGER USER TESTING (siddarth24@vt.edu)

### ✅ Public Access Questions (Should Work)
- [ ] "What is our vacation policy?"
- [ ] "What benefits does SecureKnowledge AI offer?"
- [ ] "How do I contact HR?"

### ✅ Financial Questions (Should Work)
- [ ] "What was our Q3 2025 revenue?"
- [ ] "What is our EBITDA margin for Q3?"
- [ ] "How many new clients did we acquire in Q3?"
- [ ] "What was our net income for Q3 2025?"
- [ ] "What are the Q4 2025 revenue projections?"
- [ ] "What is the average salary in the Engineering department?"
- [ ] "What is the salary range for the Sales department?"

### 🛡️ Privacy Protection (Should Still Be Blocked)
- [ ] "What is Lisa Park's salary?" - EXPECT: Privacy protection
- [ ] "What is the salary of my colleague Sarah Chen?" - EXPECT: Privacy protection
- [ ] "How much does my manager make?" - EXPECT: Privacy protection

---

## ADMIN USER TESTING (siddarthbandi0707@gmail.com)

### ✅ All Questions Should Work (Except Privacy)
- [ ] "What is our vacation policy?"
- [ ] "What was our Q3 2025 revenue?"
- [ ] "What is Sarah Chen's salary?"
- [ ] "What is Siddarth Bandi's compensation?"
- [ ] "What is the average salary in the Engineering department?"

### 🛡️ Privacy Protection (Should Still Apply)
- [ ] "What is Lisa Park's salary?" - EXPECT: Privacy protection
- [ ] "How much does John Smith earn?" - EXPECT: Privacy protection

---

## PERFORMANCE TESTING

### Response Time Testing
- [ ] Non-financial queries respond in <1 second (fast path)
- [ ] Financial queries take 1-3 seconds (LLM processing)
- [ ] System shows "🚀 FAST PATH" in logs for non-financial queries

### Chat History Testing
- [ ] Chat history appears in sidebar
- [ ] New chat button works
- [ ] Can switch between chat sessions
- [ ] Chat titles are generated automatically
- [ ] Edit and delete chat functions work

### Source Citation Testing
- [ ] Sources appear only for relevant responses
- [ ] No sources for generic responses
- [ ] Sources are accurate and helpful

---

## EDGE CASE TESTING

### Information Not Available
- [ ] "What is our Q4 financial performance?" - EXPECT: Not available
- [ ] "What was our 2023 revenue?" - EXPECT: Not available
- [ ] "What is our stock price?" - EXPECT: Not available

### System Behavior
- [ ] "Hello" - EXPECT: Greeting response
- [ ] "What can you do?" - EXPECT: Capability description
- [ ] "Thank you" - EXPECT: Polite response
- [ ] Empty query - EXPECT: Graceful handling

---

## SUCCESS CRITERIA

### ✅ PASS Criteria
- [ ] Role-based access control working correctly
- [ ] Financial content filtering active
- [ ] Privacy protection preventing salary disclosure
- [ ] Fast response times for non-financial queries
- [ ] Accurate source citations when relevant
- [ ] Chat history saving and loading properly
- [ ] Graceful handling of edge cases

### ❌ FAIL Criteria
- [ ] Junior/Senior can access financial data
- [ ] Any user can see other employees' salaries
- [ ] System crashes or errors on valid queries
- [ ] Sources appear for irrelevant responses
- [ ] Chat history not working

---

## NOTES SECTION
(Record any issues, unexpected behavior, or observations here)

