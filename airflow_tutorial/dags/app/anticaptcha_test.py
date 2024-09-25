from common_methods import solve_captcha
import nodriver
import cdp.network
import time

async def main():
    url = "https://www.allopneus.com/liste/pneu-auto?saison%5B%5D=4seasons&saison%5B%5D=ete&saison%5B%5D=hiver&page=1"

    # Start the browser
    browser = await nodriver.start(sandbox=False)
    tab = await browser.get(url)
    cookies = await tab.send(cdp.network.get_cookies())
    
    # Solve the captcha and get the cookies and user agent
    result = solve_captcha(url, cookies)
    if isinstance(result, Exception):
        print("Failed to solve captcha:", result)
        return
    else:
        cookies, user_agent = result

    # Set user agent
    await tab.send(cdp.network.set_user_agent_override(user_agent=user_agent))

    # Set cookies
    await tab.send(cdp.network.set_cookies(cookies))
    time.sleep(2)
    # Now navigate to the URL

    # You can add additional interactions here if needed
    # For example, print the page title
    page_source = await tab.get_content()
    print("Page Source:", page_source)
    time.sleep(15)
    # Close the browser when done
    browser.stop()

# Run the asynchronous main function
nodriver.loop().run_until_complete(main())
