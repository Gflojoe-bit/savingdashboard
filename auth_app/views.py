from django.contrib.auth.views import LoginView, LogoutView


class AppLoginView(LoginView):
    template_name = "auth_app/login.html"
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    next_page = "auth_app:login"
