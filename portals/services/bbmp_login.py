# services/bbmp_login.py

from playwright.sync_api import sync_playwright, TimeoutError

def login_user(mobile: str, password: str):
    try:
        with sync_playwright() as p:
            print("Launching browser...")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            print("Navigating to BBMP portal...")
            page.goto("https://www.smartoneblr.com/BBMPServices.htm")

            print("Clicking Login/Register button...")
            page.click("text=Login/Register")

            # Wait for Mobile Number input to appear (implies modal is ready)
            print("Waiting for Mobile Number input (#username)...")
            page.wait_for_selector("#username", timeout=10000)

            print("Filling Mobile Number...")
            page.fill("#username", mobile)
            print(f"Filled mobile: {mobile}")

            print("Filling Password...")
            page.fill("#password", password)
            print("Filled password")

            print("Please manually fill the Captcha in the opened browser window.")

            # Wait until user fills captcha manually and login occurs
            print("Waiting for login to complete...")
            page.wait_for_selector("text=Welcome", timeout=120000)
            print("Login successful!")

            print("Login success detected, saving session state...")
            context.storage_state(path="bbmp_auth.json")

            browser.close()
            return True, "Login successful"

    except TimeoutError as e:
        print(f"Timeout error: {e}")
        return False, "Login failed or captcha not solved in time"

    except Exception as e:
        print(f"Exception occurred: {e}")
        return False, f"Error: {str(e)}"