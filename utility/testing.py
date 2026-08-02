from locust import HttpUser, task, between

class DisciplineUser(HttpUser):
    wait_time = between(1, 3)

    
    def on_start(self):
        """Log in once at the start — all tasks reuse this session."""
        # Step 1: Get the login page to grab a CSRF token
        response = self.client.get("/v1/login/")
        
        # Step 2: Extract CSRF token from the cookie
        csrf_token = response.cookies.get('csrftoken', '')
        
        # Step 3: POST login credentials
        self.client.post(
            "/v1/redirect_url/origin_login/",
            data={
                "email": "lastissa11@gmail.com",     # replace with a real test account
                "password": "Allahu123",     # replace with real password
            },
            headers={"X-CSRFToken": csrf_token},
            params={"login_account": "True"},
        )
        # Now the session cookie is stored and all @tasks use it
    
    # ── Public pages ──
    @task(5)
    def landing_page(self):
        self.client.get("/v1/")

    @task(3)
    def login_page(self):
        self.client.get("/v1/login/")

    @task(3)
    def signup_page(self):
        self.client.get("/v1/signup/")

    @task(2)
    def weekly_analysis(self):
        self.client.get("/v1/weekly-analysis/")

    @task(2)
    def password_reset(self):
        self.client.get("/v1/password-reset/")

    @task(1)
    def extras(self):
        self.client.get("/v1/extra/")

    @task(1)
    def in_progress(self):
        self.client.get("/v1/in-progress/")

    # ── Authenticated pages ──
    @task(6)
    def dashboard(self):
        self.client.get("/v1/dashboard/")

    @task(2)
    def onboarding(self):
        self.client.get("/v1/onboarding/")

    @task(2)
    def dashboard_settings(self):
        self.client.get("/v1/dashboard/settings/")

    @task(1)
    def each_commitment(self):
        self.client.get("/v1/dashboard/commitment/1/")

    @task(1)
    def search_friend(self):
        self.client.post("/v1/search_friend/", data={"uuid": "testuser01"})

    # ── API / data endpoints (authenticated) ──
    @task(3)
    def commitment_data(self):
        self.client.get("/v1/user_commitment_data/")

    @task(3)
    def heatmap(self):
        self.client.get("/v1/user_heat_map/")

    @task(2)
    def partner_widget(self):
        self.client.get("/v1/user_partner_widget/")

    @task(2)
    def user_picture(self):
        self.client.get("/v1/user_picture_data/")
    @task(5)
    def dashboard(self):
        self.client.get("/v1/dashboard/")