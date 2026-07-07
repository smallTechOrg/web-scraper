# portals/services/bbmp_login.py

from playwright.sync_api import TimeoutError
from portals.captcha_solver import solve_captcha
import traceback

def check_user_logged_in(page):
    """Check if the user is logged in by looking for logged-in indicators.
    
    Returns True if logged in, False otherwise.
    """
    try:
        # Check for "Welcome" text which indicates logged-in state
        welcome_element = page.locator("text=Welcome")
        if welcome_element.count() > 0 and welcome_element.first.is_visible(timeout=60000):
            print("✅ User is logged in (found Welcome text)")
            return True
        
        # Check if Login/Register button is visible (not logged in)
        login_button = page.locator("text=Login/Register")
        if login_button.count() > 0 and login_button.first.is_visible(timeout=60000):
            print("⚠️ User is not logged in (Login/Register button visible)")
            return False
            
        print("⚠️ Login status unclear")
        return False
    except Exception as e:
        print(f"⚠️ Error checking login status: {e}")
        return False


def login_user(mobile: str, password: str, page):
    """Login to BBMP portal using an existing page.
    
    This function is always called by the complaint report, so it expects
    a page object to be passed. Login happens on the same page without
    opening a new browser.
    
    Args:
        mobile: User's mobile number
        password: User's password
        page: Playwright page object (must be provided)
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Use existing page - navigate to BBMP portal if not already there
        print("Using existing page for login...")
        current_url = page.url
        if "smartoneblr.com" in current_url:

            print("Clicking Login/Register button...")
            page.click("text=Login/Register")

            # Pick the modal that actually contains the login form
            print("Waiting for login modal to appear...")
            login_modal = page.locator(".modal-dialog.modal-sm", has=page.locator("#username"))
            login_modal.wait_for(state="visible", timeout=60000)
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
                captcha_frame.locator("body").wait_for(state="visible", timeout=60000)
                
                # Try to screenshot the body or img element inside frame
                try:
                    captcha_frame.locator("img").screenshot(path=captcha_path)
                except Exception:
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

                # Try the selector confirmed to work on this site first, then fall
                # back to alternatives (with short timeouts) in case the markup changes.
                selectors = [
                    "input[placeholder*='captcha' i]",
                    "input[name='WordVerification']",
                    "#MXX",
                    "input[name='captcha']",
                    "input[id*='captcha']",
                    "input[placeholder*='verification' i]",
                    "input:not([name*='username']):not([name*='password']):visible"
                ]

                captcha_input = None
                for i, selector in enumerate(selectors):
                    print(f"Trying selector: {selector}...")
                    temp_input = modal_body.locator(selector)
                    try:
                        temp_input.wait_for(state="visible", timeout=60000 if i == 0 else 3000)
                        print(f"✓ Found with selector: {selector}")
                        captcha_input = temp_input
                        break
                    except TimeoutError:
                        print(f"✗ Not found: {selector}")

                if not captcha_input:
                    # Debug: Print all input elements in the modal
                    print("🔍 Inspecting modal HTML structure...")
                    modal_html = login_modal.inner_html()
                    print(f"Modal HTML: {modal_html[:500]}...")  # Print first 500 chars

                    # Get all inputs in modal
                    print("🔍 All input elements in modal:")
                    all_inputs = modal_body.locator("input")
                    count = all_inputs.count()
                    print(f"Total inputs found: {count}")
                    for i in range(min(count, 5)):
                        try:
                            input_elem = all_inputs.nth(i)
                            input_attrs = input_elem.get_attribute("outerHTML")
                            print(f"Input {i}: {input_attrs}")
                        except Exception:
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
                sign_in_button.wait_for(state="visible", timeout=60000)
                page.wait_for_timeout(200)  # Brief delay to ensure captcha is fully processed
                
                # The site validates the captcha entirely client-side - a wrong
                # captcha never contacts the server at all, so DOM signals like the
                # #popup_message alert are unreliable (the site never clears that
                # text, even after a later successful login). The one reliable
                # signal is the actual login validation call, which only fires when
                # the captcha is right: POST .../dwr/call/plaincall/HomePagelogin.LoginVaildation.dwr
                # A correct login returns a user record containing "loginid:"; a
                # wrong password returns without it. We read the response via
                # route.fetch() (rather than page.expect_response + response.text())
                # because the site's JS callback triggers a page navigation the
                # instant this response lands, and a follow-up CDP call to read an
                # already-received response's body often loses the race ("No
                # resource with given identifier found"); route.fetch() reads the
                # body as part of making the request, so there's nothing to race.
                welcome_locator = page.locator("text=Welcome")
                dwr_result = {"body": None, "received": False}

                # Must take exactly one parameter: Playwright inspects handler
                # arity and calls handler(route, request) for a 2-arg handler,
                # which would clobber a second param via positional args.
                def _handle_login_dwr_route(route):
                    response = route.fetch()
                    try:
                        dwr_result["body"] = response.text()
                    except Exception:
                        dwr_result["body"] = None
                    dwr_result["received"] = True
                    route.fulfill(response=response)

                dwr_url_pattern = "**/dwr/call/plaincall/HomePagelogin.LoginVaildation.dwr"
                page.route(dwr_url_pattern, _handle_login_dwr_route)

                print("Clicking Sign In and waiting for server login validation call...")
                sign_in_button.click()

                elapsed_wait_ms = 0
                while not dwr_result["received"] and elapsed_wait_ms < 15000:
                    page.wait_for_timeout(200)
                    elapsed_wait_ms += 200

                page.unroute(dwr_url_pattern, _handle_login_dwr_route)

                login_response_body = dwr_result["body"] if dwr_result["received"] else None

                if login_response_body is None:
                    # No validation call fired - the captcha was rejected client-side
                    # before the server was ever contacted.
                    print("❌ Captcha rejected client-side (no server call fired), refreshing and retrying...")
                    login_modal.locator("i.fa-refresh").click()
                    page.wait_for_timeout(800)
                    continue

                if "loginid:" not in login_response_body:
                    # Captcha was accepted (the server call fired at all), but the
                    # returned record has no user data - mobile/password are wrong.
                    # Retrying with a new captcha won't fix bad credentials.
                    print("❌ Server rejected credentials (captcha was correct, mobile/password wrong)")
                    return False, "Invalid mobile number or password"

                print("Captcha and credentials accepted by server, waiting for page to finish logging in...")
                try:
                    welcome_locator.wait_for(state="visible", timeout=15000)
                    print("✅ Login successful!")
                    success = True
                    break
                except TimeoutError:
                    try:
                        login_modal.wait_for(state="hidden", timeout=5000)
                        print("✅ Modal closed, assuming login successful!")
                        success = True
                        break
                    except TimeoutError:
                        print("❌ Credentials validated but page never completed login, refreshing captcha and retrying...")
                        login_modal.locator("i.fa-refresh").click()
                        page.wait_for_timeout(800)

            if not success:
                return False, "Captcha solving failed after retries"

            print("Saving session state to bbmp_auth.json ...")
            # Get context from page and save auth state
            context = page.context
            context.storage_state(path="bbmp_auth.json")

            return True, "Login successful (captcha auto-solved)"

    except TimeoutError:
        print("⏰ Timeout error during login:")
        traceback.print_exc()
        return False, "Login failed due to timeout"

    except Exception as e:
        print("🔥 Exception during login:")
        traceback.print_exc()
        return False, f"Error: {str(e)}"

    # Fallback return - should not reach here
    return False, "Unknown error in login_user"