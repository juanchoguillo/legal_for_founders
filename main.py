import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.utilities import ArxivAPIWrapper, WikipediaAPIWrapper
from langchain_community.tools import ArxivQueryRun, WikipediaQueryRun, DuckDuckGoSearchRun
from langchain.agents import initialize_agent, AgentType
from langchain.callbacks import StreamlitCallbackHandler
import smtplib
from email.mime.text import MIMEText
import os 
from dotenv import load_dotenv
import time
import random

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Custom CSS for responsiveness
st.markdown("""
    <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Responsive design for different screen sizes */
        @media (max-width: 768px) {
            .stApp {
                padding: 1rem;
            }
            .stTextInput > div > div > input {
                font-size: 14px;
            }
            .stMarkdown {
                font-size: 14px;
            }
        }
        
        /* Loading animation styles */
        .loading-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(255, 255, 255, 0.8);
            z-index: 9999;
        }
        
        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #3498db;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Button container styles */
        .button-container {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

ASSOCIATED_ATTORNEYS = [
    {
        "name": "David H. Pierce",
        "specialty": "Technology Startup Legal Services",
        "website": "https://founderslegal.com/practitioners/david-pierce/",
    },
]

def get_attorney_recommendation(attorney):
    attorney_recommendation = f"""\n\nFor professional legal advice, 
    I recommend consulting with [{attorney['name']}]({attorney['website']}), 
    a specialist in  {attorney['specialty']}."""
    
    return attorney_recommendation

def show_loading_screen():
    st.markdown("""
        <div class="loading-container">
            <div class="loading-spinner"></div>
        </div>
    """, unsafe_allow_html=True)

# def send_user_info(name, phone_number, user_state, conversation_summary, company_name, contact_method, subject, referred_by, message):
#     email_content = f"""
#         Name: {name}
#         Phone Number: {phone_number}
#         State: {user_state}
#         Company Name: {company_name}
#         Preferred Contact Method: {contact_method}
#         Subject: {subject}
#         Referred by: {referred_by}
#         Message: {message}

#         Conversation Summary:
#         {conversation_summary}
#     """
    
#     msg = MIMEText(email_content)
#     msg['Subject'] = f"New Startup Legal Consultation Request: {name} - {company_name}"
#     msg['From'] = "juancardona0607@gmail.com"
#     msg['To'] = "juan@bizbridge.ai"

#     try:
#         with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
#             smtp.starttls()
#             smtp.login("juancardona0607@gmail.com", os.getenv("APP_PASSWORD"))
#             smtp.send_message(msg)
#         return True
#     except Exception as e:
#         st.error(f"Error sending consultation request: {e}")
#         return False

def send_user_info(name, phone_number, user_state, conversation_summary, company_name, contact_method, subject, referred_by, message):
    email_content = f"""
    CONTACT INFO:
    Name: {name}
    Phone Number: {phone_number}
    State: {user_state}
    Company Name: {company_name}
    Preferred Contact Method: {contact_method}
    Subject: {subject}
    Referred by: {referred_by}
    Message: {message}
    
    CHAT CONVERSATION SUMMARY:
    {conversation_summary}
    """

    # List of recipient email addresses
    recipients = ["dpierce@founderslegal.com", "juancardona0607@gmail.com"]  # Add all desired email addresses here
    
    msg = MIMEText(email_content)
    msg['Subject'] = f"New Startup Legal Consultation Request: {name} - {company_name}"
    msg['From'] = "juancardona0607@gmail.com"
    msg['To'] = ", ".join(recipients)  # Join all recipients with commas
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login("juancardona0607@gmail.com", os.getenv("APP_PASSWORD"))
            # Send to all recipients
            smtp.send_message(msg, from_addr="juancardona0607@gmail.com", to_addrs=recipients)
        return True
    except Exception as e:
        st.error(f"Error sending consultation request: {e}")
        return False

def initialize_chat_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm an AI assistant for Demo Legal for Founders. How can I help you navigate the legal challenges of your startup today?"
            }
        ]
    if "assigned_attorney" not in st.session_state:
        st.session_state.assigned_attorney = random.choice(ASSOCIATED_ATTORNEYS)
    if "show_form" not in st.session_state:
        st.session_state.show_form = False

def validate_phone_number(phone_input):
    return ''.join(filter(str.isdigit, phone_input))

# def do_send_email():
#     conversation_summary=generate_conversation_summary()
#     if send_user_info(st.session_state.name, st.session_state.phone_number, st.session_state.user_state, conversation_summary):
#         st.session_state.loading = True
#         show_loading_screen()
#         time.sleep(0.3)
#         st.session_state.user_info_submitted = True
#         st.rerun()

def generate_conversation_summary():
    # Use the same LLM configuration as in the chat interface
    llm = ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"), 
        model_name="gemma2-9b-it", 
        streaming=True
    )
    
    # Collect conversation text
    conversation_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in st.session_state.messages])
    
    # Prompt for summarization
    summarization_prompt = f"""
    Please provide a concise, professional summary of the following conversation. 
    Create a single, coherent paragraph that captures the main topics, key questions, and insights. 
    Avoid bullet points or formatting. Write in a clear, conversational tone.

    Conversation:
    {conversation_text}

    Summary:
    """
    
    try:
        # Generate summary using the LLM
        response = llm.invoke(summarization_prompt)
        
        # Extract the text content from the response
        summary = response.content.split('\n')[0].strip()
        
        return summary
    except Exception as e:
        # Fallback summary if generation fails
        st.error(f"Error generating summary: {e}")
        return "A consultation was conducted with an AI assistant discussing various startup legal topics."
    
def show_chat_interface():
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg['content'])

    if prompt := st.chat_input(placeholder="How can I help you?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        llm = ChatGroq(
            groq_api_key=api_key, 
            model_name="gemma2-9b-it", 
            streaming=True
        )
        
        tools = [
            WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=1000)),
            ArxivQueryRun(api_wrapper=ArxivAPIWrapper(top_k_results=1, doc_content_chars_max=1000)),
            DuckDuckGoSearchRun(name="Search")
        ]

        prompt_for_search_agent = """
        You are an AI assistant fo David Pierce, who works in Demo Legal for Founders, a boutique law firm specializing in supporting technology founders, investors, and executives. Your purpose is to provide precise, strategic legal guidance tailored to the unique challenges of innovative startups.
        
        About David Pierce:
        David Pierce is a corporate attorney specializing in guiding high-growth SaaS companies through various stages of their lifecycle.
        Leveraging his decade-long experience in the technology sector as a sales consultant, David possesses a unique understanding of the industry's challenges and opportunities. He excels at negotiating complex technology contracts, streamlining sales processes, and building strategic partnerships for his clients.
        Beyond his expertise in software and intellectual property (IP) licensing, David also assists businesses in establishing and managing trademark portfolios. His passion for IP extends to real estate, where he advises investment groups on fund formation and property management.
        David is deeply involved in the Atlanta startup community, regularly lecturing at incubators and accelerators, including those focused on diversity, equity, and inclusion.
        His client-centric approach, coupled with his industry knowledge and negotiation skills, has earned him recognition as a "One to Watch" by Best Lawyers since 2023. David's notable projects include leading international mergers and acquisitions, negotiating complex data migration agreements, and drafting commercial software and SaaS agreements for prominent clients.  

        When responding, always follow this format:
        Thought: Think about what information or resources would be most helpful
        Action: Choose one of the available tools (Search, Wikipedia, or Arxiv)
        Action Input: The specific query to search for
        Observation: Review the search results
        Thought: Analyze if the information is sufficient or if more searching is needed
        Final Answer: Provide the complete response to the user

        Remember to:
        1. Be clear and concise
        2. Use simple language
        3. Always provide actionable information
        4. Suggest consulting with an attorney for complex matters
        """

        search_agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True,
            verbose=True,
            agent_kwargs={
                "format_instructions": prompt_for_search_agent
            }
        )
        
        with st.chat_message("assistant"):
            st_cb = StreamlitCallbackHandler(st.container(), expand_new_thoughts=False)
            
            try:
                response = search_agent.invoke(
                    {"input": prompt},
                    callbacks=[st_cb]
                )
                
                response_text = response.get('output', "I'm sorry, I couldn't process your question. Please try rephrasing it.")
                full_response = response_text + get_attorney_recommendation(st.session_state.assigned_attorney)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                st.write(full_response)
            except Exception as e:
                error_message = f"I'm sorry, there was an error processing your question. Please try rephrasing it in a different way."
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

def show_user_form():
    st.subheader("Contact David")
    
    # Basic Information
    st.session_state.name = st.text_input("Enter Your Name:")
    st.session_state.company_name = st.text_input("Company Name:")
    
    # Contact Information
    phone_input = st.text_input("Enter your phone number:", 
                            help="Just number for this field")
    st.session_state.phone_number = validate_phone_number(phone_input)
    if phone_input != st.session_state.phone_number:
        st.warning("Please enter only numbers in the phone field.")
    
    # Preferred Contact Method
    st.session_state.contact_method = st.radio(
        "Preferred Method of Contact:",
        options=["Email", "Phone"],
        horizontal=True
    )
    
    # State Selection
    states = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 
            'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 
            'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 
            'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 
            'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 
            'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 
            'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 
            'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 
            'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 
            'West Virginia', 'Wisconsin', 'Wyoming']
    st.session_state.user_state = st.selectbox("Select your state:", states)
    
    # Additional Information
    st.session_state.subject = st.text_input("Subject:")
    st.session_state.referred_by = st.text_input("Referred by:")
    st.session_state.message = st.text_area("Message:", height=100)
    
    # Disclaimer
    st.markdown("""
    <div style='font-size: 12px; color: #666; margin-top: 20px; margin-bottom: 20px;'>
    To facilitate a conversation with our attorneys, you consent to being added to our contact database 
    and to receive email and phone calls from our company. We do not distribute your information to any 
    third parties. Please acknowledge that your submission does not form an Attorney-Client relationship. 
    Do not include any confidential information. An Attorney-Client relationship with any attorneys of 
    this company (the 'Firm') can only be established after all parties have fully executed the Firm's 
    engagement letter.
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for the buttons
    col1, col2 = st.columns(2)
    
    # Submit button in the first column
    with col1:
        if st.button("Submit", use_container_width=True):
            if (st.session_state.name and st.session_state.phone_number and 
                st.session_state.user_state and st.session_state.company_name and 
                st.session_state.subject):
                conversation_summary = generate_conversation_summary()
                if send_user_info(
                    st.session_state.name,
                    st.session_state.phone_number,
                    st.session_state.user_state,
                    conversation_summary,
                    st.session_state.company_name,
                    st.session_state.contact_method,
                    st.session_state.subject,
                    st.session_state.referred_by,
                    st.session_state.message
                ):
                    st.session_state.show_form = False
                    st.rerun()
            else:
                st.warning("Please fill out all required fields (Name, Phone, State, Company Name, and Subject).")
    
    # Back button in the second column
    with col2:
        if st.button("Back", use_container_width=True):
            st.session_state.show_form = False
            st.rerun()

def main():
    st.title("Tech Startup Legal Assistant")
    
    """
    This AI assistant was created by [Biz Bridge AI](https://bizbridge.ai/) as a demo for David Pierce. 
    In this demo, the fictional company "Legal for Founders" provides strategic 
    legal guidance to technology entrepreneurs and startups. 
    While this assistant offers general information, 
    it is not a substitute for personalized legal advice. 
    "Legal for Founders" specializes in supporting innovative technology startups.
    """

    initialize_chat_state()
    
    if not st.session_state.show_form:
        show_chat_interface()
        if st.button("Get more Info"):
            st.session_state.show_form = True
            st.rerun()
    else:
        show_user_form()

if __name__ == "__main__":
    main()
