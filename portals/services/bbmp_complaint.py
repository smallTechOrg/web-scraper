# portals/services/bbmp_complaint.py

from playwright.sync_api import sync_playwright, TimeoutError
import traceback


def raise_complaint(category, subcategory, description, image_path, latitude, longitude, use_other_location):
    try:
        print("Launching browser...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(storage_state="bbmp_auth.json")
            page = context.new_page()

            print("Opening BBMP portal...")
            page.goto("https://www.smartoneblr.com/BBMPServices.htm", timeout=60000)

            print("Clicking Sahaya 2.0...")
            page.click("text=BBMP (SAHAYA 2.0)")

            print("Waiting for Sahaya page to load...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

            # ===== Detect Sahaya iframe =====
            frame = None
            print("Detecting frames...")
            for f in page.frames:
                print("Frame URL:", f.url)
                if "WssBBMPComplaintRequest" in f.url:
                    frame = f
                    break

            if frame is None:
                raise Exception("❌ Could not find Sahaya complaint iframe")
            print("✅ Using Sahaya iframe:", frame.url)

            # ===== CATEGORY =====
            print("Selecting category...")
            cat_select = frame.locator("select#typeId")
            cat_select.wait_for(state="visible", timeout=20000)
            cat_select.select_option(label=category)
            cat_select.dispatch_event("change")
            cat_select.dispatch_event("input")
            frame.wait_for_timeout(1500)

            # ===== SUBCATEGORY =====
            print("Locating subcategory dropdown...")
            sub_select = None
            for sel in ["select#subTypeId", "select#subCategoryId", "select[name*='sub']"]:
                loc = frame.locator(sel)
                if loc.count() > 0:
                    sub_select = loc
                    break

            if sub_select is None:
                all_selects = frame.locator("select")
                if all_selects.count() < 2:
                    raise Exception("❌ Could not find subcategory dropdown")
                sub_select = all_selects.nth(1)

            sub_select.wait_for(state="attached", timeout=15000)

            print("Waiting for subcategory options to load...")
            for _ in range(15):
                options = sub_select.locator("option").all_inner_texts()
                if len(options) > 1:
                    break
                frame.wait_for_timeout(1000)

            options = sub_select.locator("option").all_inner_texts()
            if len(options) <= 1:
                raise Exception("❌ Subcategory dropdown did not populate")

            print("Selecting subcategory...")
            sub_select.select_option(label=subcategory)

            # ===== DESCRIPTION =====
            print("Locating description input...")
            desc_input = None
            for sel in [
                "textarea#description",
                "textarea[name*='description']",
                "textarea",
                "input[name*='description']",
                "input[type='text']"
            ]:
                loc = frame.locator(sel)
                if loc.count() > 0:
                    desc_input = loc.first
                    print(f"Found description field using selector: {sel}")
                    break

            if desc_input is None:
                raise Exception("❌ Could not find description input field")

            desc_input.wait_for(state="attached", timeout=10000)
            desc_input.scroll_into_view_if_needed()
            desc_input.fill(description)

            # ===== IMAGE UPLOAD =====
            print("Uploading image...")
            file_input = None
            for sel in [
                "input#docOthFileName0",
                "input[name^='docOthFileName']",
                "input.file-input"
            ]:
                loc = frame.locator(sel)
                if loc.count() > 0:
                    file_input = loc.first
                    print(f"Found file input using selector: {sel}")
                    break

            if file_input is None:
                raise Exception("❌ Could not find correct file input element")

            file_input.wait_for(state="attached", timeout=10000)
            file_input.set_input_files(image_path)

            # ===== OTHER LOCATION =====
            if use_other_location:
                print("Selecting other location checkbox...")
                checkbox = frame.locator("input[type='checkbox']")
                checkbox.wait_for(state="visible", timeout=5000)
                checkbox.check()

                # ===== ADDRESS SEARCH (FIXED) =====
                print("Filling address search with lat,lng...")
                address_input = None
                for sel in [
                    "input#pac-inputnew",
                    "input#pac-input",
                    "input[placeholder='Address Search']"
                ]:
                    loc = frame.locator(sel)
                    if loc.count() > 0:
                        address_input = loc.first
                        print(f"Found address input using selector: {sel}")
                        break

                if address_input is None:
                    raise Exception("❌ Could not find address search input")

                address_input.wait_for(state="visible", timeout=10000)
                address_input.fill(f"{latitude}, {longitude}")
                page.keyboard.press("Enter")
                frame.wait_for_timeout(2000)

            # ===== SUBMIT =====
            print("Submitting complaint...")
            submit_btn = frame.locator("button:has-text('Submit')")
            submit_btn.wait_for(state="visible", timeout=15000)
            submit_btn.scroll_into_view_if_needed()
            submit_btn.click()

            print("Submitted. Waiting 60 seconds for observation (page will stay open)...")
            page.wait_for_timeout(60_000)  # 60 seconds

            print("Done observing post-submit state.")

            print("Waiting for submission confirmation...")
            frame.wait_for_timeout(5000)

            print("✅ Complaint submitted successfully")
            browser.close()
            return True, "Complaint submitted successfully"

    except TimeoutError:
        print("⏰ Timeout during complaint submission")
        traceback.print_exc()
        return False, "Timeout while submitting complaint"

    except Exception as e:
        print("🔥 Exception during complaint submission")
        traceback.print_exc()
        return False, f"Error: {str(e)}"