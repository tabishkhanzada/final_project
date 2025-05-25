import streamlit as st
import urllib.parse
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import plotly.express as px
import pandas as pd

def configure_page():
    st.set_page_config(page_title="LinkedIn Job Insights", layout="wide")
    st.title("🔍 LinkedIn Job Insights")
    st.write("Discover job statistics and top hiring companies")

def generate_linkedin_url(keyword, location):
    base_url = "https://www.linkedin.com/jobs/search/"
    params = {
        'keywords': keyword,
        'location': location,
        'position': 1,
        'pageNum': 0
    }
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def setup_browser():
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")
    headless = True
    if headless:
        chrome_options.add_argument("--headless=new")
    try:
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=chrome_options)
        browser.set_page_load_timeout(60)
        return browser
    except Exception as e:
        st.error(f"Browser setup failed: {str(e)}")
        return None

def scrape_linkedin_jobs(keyword, location):
    browser = setup_browser()
    if not browser:
        return None

    try:
        url = generate_linkedin_url(keyword, location)
        browser.get(url)

        WebDriverWait(browser, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        data = {
            "total_jobs": "Data not available",
            "salary_range": "Data not available",
            "work_types": {"Onsite": 0, "Remote": 0, "Hybrid": 0},
            "companies": [],
            "search_url": url
        }

        try:
            total_jobs_elem = browser.find_element(By.CLASS_NAME, "results-context-header__job-count")
            data["total_jobs"] = total_jobs_elem.text.strip()
        except:
            pass

        # Work Types - Based on job metadata wrapper content
        try:
            job_cards_metadata = browser.find_elements(By.CLASS_NAME, "job-card-container__metadata-wrapper")
            for meta in job_cards_metadata:
                text = meta.text.lower()
            if "remote" in text:
                data["work_types"]["Remote"] += 1
            elif "on-site" in text or "onsite" in text:
                data["work_types"]["Onsite"] += 1
            elif "hybrid" in text:
                data["work_types"]["Hybrid"] += 1
        except Exception as e:
            print("Work type scraping error:", e)


        try:
            time.sleep(2)
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            companies = browser.find_elements(By.CSS_SELECTOR, ".base-search-card__subtitle")
            data["companies"] = list({c.text for c in companies if c.text})[:10]
        except:
            pass

        return data

    except Exception as e:
        st.error(f"Scraping failed: {e}")
        return None
    finally:
        try:
            browser.quit()
        except:
            pass

def display_results(job_data, keyword):
    if not job_data:
        st.error("No data found.")
        return

    st.subheader("📊 Job Market Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Jobs", job_data["total_jobs"])
    col2.metric("Salary Range", job_data["salary_range"])
    
    with col3:
        st.write("**Work Types**")
        st.write(f"🏢 Onsite: {job_data['work_types']['Onsite']}")
        st.write(f"🏠 Remote: {job_data['work_types']['Remote']}")
        st.write(f"🔀 Hybrid: {job_data['work_types']['Hybrid']}")

    # Work Types Pie Chart
    st.subheader("📌 Work Type Distribution")
    work_df = pd.DataFrame({
        "Type": ["Onsite", "Remote", "Hybrid"],
        "Count": [
            job_data["work_types"]["Onsite"],
            job_data["work_types"]["Remote"],
            job_data["work_types"]["Hybrid"]
        ]
    })
    fig = px.pie(work_df, names='Type', values='Count', title="Work Type Split", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # Company Bar Chart
    st.subheader("🏢 Top Hiring Companies")
    if job_data["companies"]:
        companies_df = pd.DataFrame({"Company": job_data["companies"]})
        companies_df["Count"] = 1
        fig2 = px.bar(companies_df, x="Company", y="Count", title="Top Hiring Companies")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.write("No company data found.")

    st.markdown(f"""### 🔗 [View Jobs on LinkedIn]({job_data['search_url']})""")

    # Conclusion
    st.subheader("✅ Conclusion")
    st.markdown(f"""
    The field of **{keyword}** appears to be in high demand based on current LinkedIn data.
    There are a significant number of remote, hybrid, and onsite opportunities available,
    showing how flexible and growing this career path is. It’s a great time to upskill and pursue a job in this domain!
    """)

def main():
    configure_page()
    
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        with col1:
            keyword = st.text_input("Job Title", "Python Developer")
        with col2:
            location = st.text_input("Location", "India")
        submitted = st.form_submit_button("Search Jobs")

    if submitted:
        with st.spinner("Scraping data from LinkedIn..."):
            job_data = scrape_linkedin_jobs(keyword, location)
            if job_data:
                display_results(job_data, keyword)
                st.success("Done!")
            else:
                st.error("Could not retrieve data.")

if __name__ == "__main__":
    main()
