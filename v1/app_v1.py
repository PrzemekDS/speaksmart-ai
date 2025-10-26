import streamlit as st
import openai
import pandas as pd
import json
from datetime import datetime
import re

# --- Translation counter ---
if "translation_count" not in st.session_state:
    st.session_state.translation_count = 0

# Configure page
st.set_page_config(
    page_title="MY Translator App",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stTextInput > div > div > input {
        background-color: #2b2b2b;
        color: white;
        border: 1px solid #4a4a4a;
    }
    .stTextArea > div > div > textarea {
        background-color: #2b2b2b;
        color: white;
        border: 1px solid #4a4a4a;
    }
    .stSelectbox > div > div > select {
        background-color: #2b2b2b;
        color: white;
        border: 1px solid #4a4a4a;
    }
    .success {
        color: #00ff00;
        font-weight: bold;
    }
    .error {
        color: #ff4444;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1e1e1e;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #4a4a4a;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'translations' not in st.session_state:
    st.session_state.translations = []
if 'vocabulary' not in st.session_state:
    st.session_state.vocabulary = []
if 'total_cost' not in st.session_state:
    st.session_state.total_cost = 0.0
if 'total_translations' not in st.session_state:
    st.session_state.total_translations = 0

def calculate_usage_cost(response):
    """Calculate cost based on token usage"""
    try:
        usage = response.usage
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        # GPT-4o-mini pricing (as of 2024)
        input_cost_per_1k = 0.00015  # $0.15 per 1M tokens
        output_cost_per_1k = 0.0006  # $0.60 per 1M tokens
        
        cost = (input_tokens / 1000 * input_cost_per_1k) + (output_tokens / 1000 * output_cost_per_1k)
        return cost, input_tokens, output_tokens
    except:
        return 0.0, 0, 0

def detect_language(text, api_key):
    """Detect source language using OpenAI"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Detect the language of the given text. Respond with only the language name in English (e.g., 'English', 'Polish', 'Spanish', etc.)."},
                {"role": "user", "content": text}
            ],
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Language detection error: {str(e)}")
        return "Unknown"

def translate_text(text, target_lang, api_key):
    """Translate text using OpenAI"""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Translate the following text to {target_lang}. Provide only the translation without any explanations."},
                {"role": "user", "content": text}
            ],
            max_tokens=1000
        )
        return response
    except Exception as e:
        st.error(f"Translation error: {str(e)}")
        return None

def clean_output(text):
    """Clean and format output text"""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    return text

# Sidebar
with st.sidebar:
    st.title("🌐 Translator")
    
    # API Key input
    api_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key")
    
    # Target language
    target_lang = st.text_input("Target Language", value="angielski", help="Language to translate to")
    
    st.markdown("---")
    
    # Translation stats
    st.subheader("📊 Statistics")
    
    if st.session_state.total_translations > 0:
        # Get last translation stats
        last_translation = st.session_state.translations[-1] if st.session_state.translations else None
        if last_translation:
            st.metric("Input Tokens", last_translation.get('input_tokens', 0))
            st.metric("Output Tokens", last_translation.get('output_tokens', 0))
            st.metric("Last Cost", f"${last_translation.get('cost', 0):.4f}")
    
    st.metric("Total Cost", f"${st.session_state.total_cost:.4f}")
    
    # Progress bar (0-1 USD)
    progress = min(st.session_state.total_cost / 1.0, 1.0)
    st.progress(progress)
    st.caption(f"Usage: {st.session_state.total_cost:.4f}/$1.00")
    
    st.metric("Translations", st.session_state.total_translations)
    
    st.markdown("---")
    
    # Export vocabulary
    if st.session_state.vocabulary:
        vocab_df = pd.DataFrame(st.session_state.vocabulary)
        csv = vocab_df.to_csv(index=False)
        st.download_button(
            label="📥 Export Vocabulary",
            data=csv,
            file_name=f"vocabulary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Main area
st.title("🌐 AI Translator")

# Text input
input_text = st.text_area(
    "Enter text to translate:",
    height=150,
    placeholder="Type your text here..."
)

# Translate button
if st.button("🔄 Przetłumacz", type="primary"):
    if not api_key:
        st.error("Please enter your OpenAI API key in the sidebar.")
    elif not input_text.strip():
        st.error("Please enter some text to translate.")
    else:
        with st.spinner("Translating..."):
            # Detect language
            detected_lang = detect_language(input_text, api_key)
            st.info(f"Detected language: {detected_lang}")
            
            # Translate
            response = translate_text(input_text, target_lang, api_key)
            
            if response:
                translation = clean_output(response.choices[0].message.content)
                cost, input_tokens, output_tokens = calculate_usage_cost(response)
                
                # Store translation
                translation_data = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'source_text': input_text,
                    'target_text': translation,
                    'source_language': detected_lang,
                    'target_language': target_lang,
                    'cost': cost,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                }
                
                st.session_state.translations.append(translation_data)
                st.session_state.total_cost += cost
                st.session_state.total_translations += 1
                
                # Display translation
                st.success("Translation completed!")

                # Increment translation counter
                st.session_state.translation_count += 1
                st.info(f"Translation #{st.session_state.translation_count}")

                st.text_area("Translation:", value=translation, height=150, disabled=True)
                
                # Add to vocabulary button
                if st.button("💾 Dodaj do mojego słownika", key="add_to_vocab"):
                    vocab_item = {
                        'source': input_text,
                        'translation': translation,
                        'source_lang': detected_lang,
                        'target_lang': target_lang,
                        'added_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.vocabulary.append(vocab_item)
                    st.success("Added to vocabulary!")

# Vocabulary section
st.markdown("---")
st.subheader("📚 My Vocabulary")

if st.session_state.vocabulary:
    # Display vocabulary with delete options
    for i, item in enumerate(st.session_state.vocabulary):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.write(f"**{item['source']}** → {item['translation']}")
            st.caption(f"{item['source_lang']} → {item['target_lang']} | Added: {item['added_date']}")
        
        with col2:
            if st.button("🗑️", key=f"delete_{i}", help="Delete this item"):
                st.session_state.vocabulary.pop(i)
                st.rerun()
else:
    st.info("No vocabulary items yet. Add some translations to build your personal dictionary!")

# Recent translations
st.markdown("---")
st.subheader("🕒 Recent Translations")

if st.session_state.translations:
    # Show last 5 translations
    recent_translations = st.session_state.translations[-5:]
    
    for i, trans in enumerate(reversed(recent_translations)):
        with st.expander(f"Translation {len(st.session_state.translations) - i} - {trans['timestamp']}"):
            st.write(f"**Source ({trans['source_language']}):** {trans['source_text']}")
            st.write(f"**Translation ({trans['target_language']}):** {trans['target_text']}")
            st.caption(f"Cost: ${trans['cost']:.6f} | Tokens: {trans['input_tokens']}+{trans['output_tokens']}")
else:
    st.info("No translations yet. Start translating to see your history here!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>🌐 AI Translator powered by OpenAI GPT-4o-mini</div>",
    unsafe_allow_html=True
)