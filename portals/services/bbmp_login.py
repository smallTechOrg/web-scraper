# portals/services/bbmp_login.py

from playwright.sync_api import sync_playwright, TimeoutError
from portals.services.captcha_solver import solve_captcha
import traceback

def login_user(mobile: str, password: str):
    try:
        print("Launching browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # keep visible while testing
            context = browser.new_context()
            page = context.new_page()

            print("Navigating to BBMP portal...")
            page.goto("https://www.smartoneblr.com/BBMPServices.htm", timeout=60000)

            print("Clicking Login/Register button...")
            page.click("text=Login/Register")

            # Pick the modal that actually contains the login form
            print("Waiting for login modal to appear...")
            login_modal = page.locator(".modal-dialog.modal-sm", has=page.locator("#username"))
            login_modal.wait_for(state="visible", timeout=15000)
            print("Login modal is visible.")

            print("Filling Mobile Number...")
            login_modal.locator("#username").fill(mobile)
            print(f"Filled mobile: {mobile}")

            print("Filling Password...")
            login_modal.locator("#password").fill(password)
            print("Filled password.")

            # Give a brief moment for captcha iframe to load
            page.wait_for_timeout(500)

            captcha_path = "captcha.png"
            success = False

            for attempt in range(3):
                print(f"\n--- Captcha attempt {attempt + 1} ---")

                print("Taking captcha screenshot...")
                captcha_frame = login_modal.frame_locator("#image")
                
                # Wait for the frame to be loaded
                captcha_frame.locator("body").wait_for(state="visible", timeout=5000)
                
                # Try to screenshot the body or img element inside frame
                try:
                    captcha_frame.locator("img").screenshot(path=captcha_path)
                except:
                    # Fallback to body screenshot if img element not found
                    captcha_frame.locator("body").screenshot(path=captcha_path)
                
                print(f"Captcha saved to {captcha_path}")

                print("Solving captcha with OCR...")
                captcha_text = solve_captcha(captcha_path)
                print("Predicted captcha:", repr(captcha_text))

                if not captcha_text:
                    print("OCR returned empty text, refreshing captcha...")
                    login_modal.locator("i.fa-refresh").click()
                    page.wait_for_timeout(600)
                    continue

                print("Locating captcha input inside modal body...")
                modal_body = login_modal.locator(".modal-body")
                
                # Debug: Print all input elements in the modal
                print("🔍 Inspecting modal HTML structure...")
                modal_html = login_modal.inner_html()
                print(f"Modal HTML: {modal_html[:500]}...")  # Print first 500 chars
                
                # Try to find captcha input with proper selector
                print("Trying selector: input[name='WordVerification']...")
                captcha_input = modal_body.locator("input[name='WordVerification']")
                
                # Check if it exists, if not try alternative selector
                try:
                    captcha_input.wait_for(state="visible", timeout=3000)
                    print("✓ Found input[name='WordVerification']")
                except TimeoutError:
                    print("✗ WordVerification input not found")
                    
                    # Try alternative selectors
                    selectors = [
                        "#MXX",
                        "input[name='captcha']",
                        "input[id*='captcha']",
                        "input[placeholder*='captcha' i]",
                        "input[placeholder*='verification' i]",
                        "input:not([name*='username']):not([name*='password']):visible"
                    ]
                    
                    captcha_input = None
                    for selector in selectors:
                        print(f"Trying selector: {selector}...")
                        temp_input = modal_body.locator(selector)
                        try:
                            temp_input.wait_for(state="visible", timeout=2000)
                            print(f"✓ Found with selector: {selector}")
                            captcha_input = temp_input
                            break
                        except TimeoutError:
                            print(f"✗ Not found: {selector}")
                    
                    if not captcha_input:
                        # Get all inputs in modal
                        print("🔍 All input elements in modal:")
                        all_inputs = modal_body.locator("input")
                        count = all_inputs.count()
                        print(f"Total inputs found: {count}")
                        for i in range(min(count, 5)):
                            try:
                                input_elem = all_inputs.nth(i)
                                input_html = input_elem.inner_html()
                                input_attrs = input_elem.get_attribute("outerHTML")
                                print(f"Input {i}: {input_attrs}")
                            except:
                                pass
                        
                        raise Exception("Cannot find captcha input element!")

                print("Clearing any existing captcha input...")
                captcha_input.clear()
                
                # Minimal waiting (no overkill)
                captcha_input.scroll_into_view_if_needed()

                print(f"Filling captcha input with: {captcha_text}")
                captcha_input.fill(captcha_text)
                
                # Verify the value was filled
                filled_value = captcha_input.input_value()
                print(f"Verification - Input value after fill: {filled_value}")
                
                # Add a small delay to ensure captcha text is fully entered
                page.wait_for_timeout(300)

                print("Clicking Sign In...")
                sign_in_button = modal_body.locator("button:has-text('Sign In')")
                sign_in_button.scroll_into_view_if_needed()
                
                # Wait for button to be enabled and clickable
                sign_in_button.wait_for(state="visible", timeout=5000)
                page.wait_for_timeout(200)  # Brief delay to ensure captcha is fully processed
                
                sign_in_button.click()

                print("Waiting for login success indicator...")
                try:
                    page.wait_for_selector("text=Welcome", timeout=8000)
                    print("✅ Login successful!")
                    success = True
                    break
                except TimeoutError:
                    # Check if we're still on login form or if modal closed
                    try:
                        login_modal.wait_for(state="hidden", timeout=2000)
                        print("✅ Modal closed, assuming login successful!")
                        success = True
                        break
                    except TimeoutError:
                        print("❌ Login failed, refreshing captcha and retrying...")
                        login_modal.locator("i.fa-refresh").click()
                        page.wait_for_timeout(800)

            if not success:
                browser.close()
                return False, "Captcha solving failed after retries"

            print("Saving session state to bbmp_auth.json ...")
            context.storage_state(path="bbmp_auth.json")

            browser.close()
            return True, "Login successful (captcha auto-solved)"

    except TimeoutError:
        print("⏰ Timeout error during login:")
        traceback.print_exc()
        return False, "Login failed due to timeout"

    except Exception as e:
        print("🔥 Exception during login:")
        traceback.print_exc()
        return False, f"Error: {str(e)}"