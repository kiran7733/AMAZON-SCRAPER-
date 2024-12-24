from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
import time
import csv
import json


class AmazonScraper:
    def __init__(self, email, password):
        self.email = email
        self.password = password

        edge_options = Options()
        edge_options.add_argument("start-maximized")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        self.driver = webdriver.Edge(options=edge_options)
        self.wait = WebDriverWait(self.driver, 15)

    def login(self):
        try:
            self.driver.get("http://www.amazon.in")

            # Click on the account list
            self.driver.find_element(By.XPATH, "//span[@id='nav-link-accountList-nav-line-1']").click()

            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_email")))
            email_field.send_keys(self.email)
            email_field.send_keys(Keys.RETURN)

            password_field = self.wait.until(EC.presence_of_element_located((By.ID, "ap_password")))
            password_field.send_keys(self.password)
            password_field.send_keys(Keys.RETURN)

            self.wait.until(EC.presence_of_element_located((By.ID, "nav-link-accountList")))
            print("Login successful")
            return True
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def get_discount_percentage(self, discount_text):
        try:
            if discount_text and discount_text != "N/A":
                return float(''.join(filter(str.isdigit, discount_text)))
            return 0
        except Exception as e:
            print(f"Error parsing discount percentage: {str(e)}")
            return 0

    def scrape_category(self, category_url):
        self.driver.get(category_url)
        filtered_products = []

        try:
            time.sleep(5)
            product_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[id^='gridItemRoot']")

            for card in product_cards[:10]:
                try:
                    product_data = {}

                    # Product Name
                    product_data["Product Name"] = self.get_text_from_element(
                        card, "div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1"
                    )

                    # Product Price
                    product_data["Product Price"] = self.get_text_from_element(
                        card, "span._cDEzb_p13n-sc-price_3mJ9Z"
                    )

                    # BestSeller Rating
                    product_data["BestSeller Rating"] = self.get_text_from_element(
                        card, "span.zg-bdg-text", default="N/A"
                    )

                    # Product URL for details
                    try:
                        product_url = card.find_element(By.CSS_SELECTOR, "a.a-link-normal").get_attribute("href")
                        detailed_data = self.get_product_details(product_url)
                        if detailed_data:
                            product_data.update(detailed_data)

                            discount_percentage = self.get_discount_percentage(
                                detailed_data.get("SaleDiscount", "N/A")
                            )
                            print(f"Discount for {product_data['Product Name']}: {discount_percentage}%")
                            if discount_percentage > 50:
                                filtered_products.append(product_data)
                                print(f"Added {product_data['Product Name']} to filtered products")
                    except Exception as e:
                        print(f"Error accessing product URL: {str(e)}")

                except Exception as e:
                    print(f"Error processing product card: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error scraping bestseller page: {str(e)}")

        return filtered_products

    def get_product_details(self, product_url):
        try:
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(product_url)
            time.sleep(3)

            details = {}

            # Sale Discount
            details["SaleDiscount"] = self.get_text_from_element(
                self.driver, "span.savingsPercentage, span.percentageToSave", default="N/A"
            )

            # Ship From
            try:
                ship_from_element = self.driver.find_element(By.XPATH,
                                                             "//span[@class='a-size-small tabular-buybox-text-message'][normalize-space()='Amazon']")
                details["ShipFrom"] = ship_from_element.text.strip()
            except Exception:
                details["ShipFrom"] = "N/A"

            # Sold By
            try:
                sold_by_element = self.driver.find_element(By.XPATH,
                                                           "//span[@class='a-size-small tabular-buybox-text-message']//a[@id='sellerProfileTriggerId']")
                details["SoldBy"] = sold_by_element.text.strip()
            except Exception:
                details["SoldBy"] = "N/A"

            # Rating
            try:
                rating = "N/A"
                try:
                    rating_element = self.wait.until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#acrPopover, span.a-icon-alt")
                    ))
                    rating = rating_element.get_attribute("title") or rating_element.text
                except:
                    try:
                        rating_element = self.driver.find_element(
                            By.CSS_SELECTOR, "span[data-hook='rating-out-of-text']"
                        )
                        rating = rating_element.text
                    except:
                        try:
                            rating_element = self.driver.find_element(
                                By.CSS_SELECTOR, "i.a-icon-star-small span.a-icon-alt"
                            )
                            rating = rating_element.text
                        except:
                            try:
                                rating_element = self.driver.find_element(
                                    By.XPATH, "//div[@id='averageCustomerReviews']//span[@class='a-icon-alt']"
                                )
                                rating = rating_element.text
                            except:
                                rating = "N/A"

                if rating and rating != "N/A":
                    rating = rating.split()[0]
                    if rating.replace('.', '').isdigit():
                        details["Rating"] = rating
                    else:
                        details["Rating"] = "N/A"
                else:
                    details["Rating"] = "N/A"

            except Exception as e:
                print(f"Error getting rating: {str(e)}")
                details["Rating"] = "N/A"

            # Product Description
            details["ProductDescription"] = self.get_text_from_element(
                self.driver, "#productDescription, #feature-bullets", default="N/A"
            )

            # Number Bought
            details["NumberBought"] = self.get_text_from_element(
                self.driver, "#social-proofing-faceout-title-tk_bought", default="N/A"
            ).split()[0]

            # Images
            details["AllAvailableImages"] = [
                img.get_attribute("src")
                for img in self.driver.find_elements(By.CSS_SELECTOR, "#altImages img")
                if "sprite" not in img.get_attribute("src")
            ]

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return details

        except Exception as e:
            print(f"Error getting product details: {str(e)}")
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            return None

    def get_text_from_element(self, context, selector, default="N/A"):
        try:
            return context.find_element(By.CSS_SELECTOR, selector).text.strip()
        except:
            return default

    def save_data(self, data, base_filename):
        if not data:
            print("No products found with discount greater than 50%")
            return

        # Save as CSV
        csv_filename = f"{base_filename}_high_discount.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        # Save as JSON
        json_filename = f"{base_filename}_high_discount.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Data saved to {csv_filename} and {json_filename}")

    def close(self):
        self.driver.quit()


def main():
    categories = [
        "https://www.amazon.in/gp/bestsellers/kitchen",
        "https://www.amazon.in/gp/bestsellers/shoes",
        "https://www.amazon.in/gp/bestsellers/computers",
        "https://www.amazon.in/gp/bestsellers/electronics",
        "https://www.amazon.in/gp/bestsellers/beauty",
        "https://www.amazon.in/gp/bestsellers/sports",
        "https://www.amazon.in/gp/bestsellers/home-improvement",
        "https://www.amazon.in/gp/bestsellers/mobile-phones",
        "https://www.amazon.in/gp/bestsellers/watches",
        "https://www.amazon.in/gp/bestsellers/luggage"
    ]

    email = input("Enter your Amazon email: ")
    password = input("Enter your Amazon password: ")

    scraper = AmazonScraper(email, password)

    if scraper.login():
        all_data = []
        for category_url in categories:
            print(f"Scraping category: {category_url}")
            category_data = scraper.scrape_category(category_url)
            all_data.extend(category_data)
            time.sleep(2)

        scraper.save_data(all_data, "amazon_bestsellers_detailed")

    scraper.close()


if __name__ == "__main__":
    main()
