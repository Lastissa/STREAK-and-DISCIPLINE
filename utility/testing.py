from locust import HttpUser, task, between

class DisciplineUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def landing_page(self):
        self.client.get("/v1/")

    @task(3)
    def login(self):
        self.client.get("/v1/login/")

    @task(3)
    def signup(self):
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