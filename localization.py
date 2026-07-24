from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"
LANGUAGE_OPTIONS = (
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("tr", "Türkçe"),
    ("ru", "Русский"),
    ("uk", "Українська"),
    ("ar", "العربية"),
    ("hi", "हिन्दी"),
    ("zh-cn", "简体中文"),
    ("zh-tw", "繁體中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("id", "Bahasa Indonesia"),
    ("vi", "Tiếng Việt"),
    ("th", "ไทย"),
)

ENGLISH = {
    "page_title": "Temporary 2FA Access",
    "language": "Language",
    "apply": "Apply",
    "lock_portal": "Lock portal",
    "access_key_required": "Access key required",
    "copy_current_code": "Copy current code",
    "tap_to_copy": "Tap to copy",
    "loading_code": "Loading code…",
    "purchase_accepted": (
        "Your purchase key has been accepted. Only the current authenticator "
        "code is shown; the permanent TOTP setup secret is never sent to the "
        "browser."
    ),
    "provider": "Provider",
    "login_email": "Login email",
    "expires": "Expires",
    "refresh": "Refresh",
    "seconds": "seconds",
    "enter_access_key": "Enter your access key",
    "unlock_intro": (
        "Use the temporary key delivered with your G2G order. It will stop "
        "working automatically when your subscription ends."
    ),
    "temporary_access_key": "Temporary access key",
    "open_authenticator": "Open authenticator",
    "how_it_works": "How it works",
    "how_it_works_body": (
        "The access key is linked to your purchase and expiration time. After "
        "it is accepted, this page provides the current code for the shared "
        "software account."
    ),
    "delivery": "Delivery",
    "g2g_order": "G2G order",
    "expiration": "Expiration",
    "automatic": "Automatic",
    "new_code_in": "New code in",
    "second": "second",
    "seconds_unit": "seconds",
    "refreshing": "Refreshing",
    "unable_to_retrieve": "Unable to retrieve the code.",
    "connection_error": "Connection error.",
    "copied": "Copied",
    "copy_failed": "Copy failed. Select the code manually.",
    "complete_key_error": "Enter the complete access key supplied with your order.",
    "rate_limit_error": "Too many failed attempts. Wait a few minutes.",
    "invalid_key_error": "Invalid access key.",
    "revoked_key_error": "This access key has been revoked.",
    "expired_key_error": "This subscription has expired.",
    "session_limit_error": "This order has reached its active-session limit.",
    "ip_limit_error": "This order has reached its distinct-IP limit.",
    "portal_not_configured": "The portal is not configured",
    "enter_key_first": "Enter your access key first",
    "access_ended": "Your access has expired or was revoked",
}

TRANSLATION_OVERRIDES: dict[str, dict[str, str]] = {
    "fr": {
        "page_title": "Accès 2FA temporaire",
        "language": "Langue",
        "apply": "Appliquer",
        "lock_portal": "Verrouiller le portail",
        "access_key_required": "Clé d’accès requise",
        "copy_current_code": "Copier le code actuel",
        "tap_to_copy": "Appuyez pour copier",
        "loading_code": "Chargement du code…",
        "purchase_accepted": (
            "Votre clé d’achat a été acceptée. Seul le code d’authentification "
            "actuel est affiché ; le secret TOTP permanent n’est jamais envoyé "
            "au navigateur."
        ),
        "provider": "Fournisseur",
        "login_email": "E-mail de connexion",
        "expires": "Expire le",
        "refresh": "Actualisation",
        "seconds": "secondes",
        "enter_access_key": "Saisissez votre clé d’accès",
        "unlock_intro": (
            "Utilisez la clé temporaire fournie avec votre commande G2G. Elle "
            "cessera automatiquement de fonctionner à la fin de votre abonnement."
        ),
        "temporary_access_key": "Clé d’accès temporaire",
        "open_authenticator": "Ouvrir l’authentificateur",
        "how_it_works": "Fonctionnement",
        "how_it_works_body": (
            "La clé d’accès est liée à votre achat et à sa date d’expiration. Une "
            "fois acceptée, cette page fournit le code actuel du compte logiciel "
            "partagé."
        ),
        "delivery": "Livraison",
        "g2g_order": "Commande G2G",
        "expiration": "Expiration",
        "automatic": "Automatique",
        "new_code_in": "Nouveau code dans",
        "second": "seconde",
        "seconds_unit": "secondes",
        "refreshing": "Actualisation",
        "unable_to_retrieve": "Impossible de récupérer le code.",
        "connection_error": "Erreur de connexion.",
        "copied": "Copié",
        "copy_failed": "Échec de la copie. Sélectionnez le code manuellement.",
        "complete_key_error": (
            "Saisissez la clé d’accès complète fournie avec votre commande."
        ),
        "rate_limit_error": (
            "Trop de tentatives ont échoué. Attendez quelques minutes."
        ),
        "invalid_key_error": "Clé d’accès invalide.",
        "revoked_key_error": "Cette clé d’accès a été révoquée.",
        "expired_key_error": "Cet abonnement a expiré.",
        "session_limit_error": (
            "Cette commande a atteint sa limite de sessions actives."
        ),
        "ip_limit_error": (
            "Cette commande a atteint sa limite d’adresses IP distinctes."
        ),
        "portal_not_configured": "Le portail n’est pas configuré",
        "enter_key_first": "Saisissez d’abord votre clé d’accès",
        "access_ended": "Votre accès a expiré ou a été révoqué",
    },
    "es": {
        "page_title": "Acceso 2FA temporal",
        "language": "Idioma",
        "apply": "Aplicar",
        "lock_portal": "Bloquear portal",
        "access_key_required": "Se requiere una clave de acceso",
        "copy_current_code": "Copiar el código actual",
        "tap_to_copy": "Pulsa para copiar",
        "loading_code": "Cargando código…",
        "purchase_accepted": (
            "Tu clave de compra ha sido aceptada. Solo se muestra el código de "
            "autenticación actual; el secreto TOTP permanente nunca se envía al "
            "navegador."
        ),
        "provider": "Proveedor",
        "login_email": "Correo de inicio de sesión",
        "expires": "Caduca",
        "refresh": "Actualización",
        "seconds": "segundos",
        "enter_access_key": "Introduce tu clave de acceso",
        "unlock_intro": (
            "Usa la clave temporal entregada con tu pedido de G2G. Dejará de "
            "funcionar automáticamente cuando termine tu suscripción."
        ),
        "temporary_access_key": "Clave de acceso temporal",
        "open_authenticator": "Abrir autenticador",
        "how_it_works": "Cómo funciona",
        "how_it_works_body": (
            "La clave de acceso está vinculada a tu compra y fecha de caducidad. "
            "Tras aceptarla, esta página proporciona el código actual de la cuenta "
            "de software compartida."
        ),
        "delivery": "Entrega",
        "g2g_order": "Pedido de G2G",
        "expiration": "Caducidad",
        "automatic": "Automática",
        "new_code_in": "Nuevo código en",
        "second": "segundo",
        "seconds_unit": "segundos",
        "refreshing": "Actualizando",
        "unable_to_retrieve": "No se puede obtener el código.",
        "connection_error": "Error de conexión.",
        "copied": "Copiado",
        "copy_failed": "Error al copiar. Selecciona el código manualmente.",
        "complete_key_error": (
            "Introduce la clave de acceso completa proporcionada con tu pedido."
        ),
        "rate_limit_error": ("Demasiados intentos fallidos. Espera unos minutos."),
        "invalid_key_error": "Clave de acceso no válida.",
        "revoked_key_error": "Esta clave de acceso ha sido revocada.",
        "expired_key_error": "Esta suscripción ha caducado.",
        "session_limit_error": (
            "Este pedido ha alcanzado su límite de sesiones activas."
        ),
        "ip_limit_error": (
            "Este pedido ha alcanzado su límite de direcciones IP distintas."
        ),
        "portal_not_configured": "El portal no está configurado",
        "enter_key_first": "Introduce primero tu clave de acceso",
        "access_ended": "Tu acceso ha caducado o ha sido revocado",
    },
    "de": {
        "page_title": "Temporärer 2FA-Zugang",
        "language": "Sprache",
        "apply": "Übernehmen",
        "lock_portal": "Portal sperren",
        "access_key_required": "Zugangsschlüssel erforderlich",
        "copy_current_code": "Aktuellen Code kopieren",
        "tap_to_copy": "Zum Kopieren tippen",
        "loading_code": "Code wird geladen…",
        "purchase_accepted": (
            "Dein Kaufschlüssel wurde akzeptiert. Es wird nur der aktuelle "
            "Authentifizierungscode angezeigt; das permanente TOTP-Geheimnis wird "
            "niemals an den Browser gesendet."
        ),
        "provider": "Anbieter",
        "login_email": "Anmelde-E-Mail",
        "expires": "Läuft ab",
        "refresh": "Aktualisierung",
        "seconds": "Sekunden",
        "enter_access_key": "Zugangsschlüssel eingeben",
        "unlock_intro": (
            "Verwende den temporären Schlüssel aus deiner G2G-Bestellung. Er "
            "funktioniert nach Ende deines Abonnements automatisch nicht mehr."
        ),
        "temporary_access_key": "Temporärer Zugangsschlüssel",
        "open_authenticator": "Authentifikator öffnen",
        "how_it_works": "So funktioniert es",
        "how_it_works_body": (
            "Der Zugangsschlüssel ist mit deinem Kauf und Ablaufdatum verknüpft. "
            "Nach der Annahme zeigt diese Seite den aktuellen Code für das "
            "gemeinsam genutzte Softwarekonto an."
        ),
        "delivery": "Lieferung",
        "g2g_order": "G2G-Bestellung",
        "expiration": "Ablauf",
        "automatic": "Automatisch",
        "new_code_in": "Neuer Code in",
        "second": "Sekunde",
        "seconds_unit": "Sekunden",
        "refreshing": "Wird aktualisiert",
        "unable_to_retrieve": "Der Code konnte nicht abgerufen werden.",
        "connection_error": "Verbindungsfehler.",
        "copied": "Kopiert",
        "copy_failed": "Kopieren fehlgeschlagen. Wähle den Code manuell aus.",
        "complete_key_error": (
            "Gib den vollständigen Zugangsschlüssel aus deiner Bestellung ein."
        ),
        "rate_limit_error": (
            "Zu viele fehlgeschlagene Versuche. Warte einige Minuten."
        ),
        "invalid_key_error": "Ungültiger Zugangsschlüssel.",
        "revoked_key_error": "Dieser Zugangsschlüssel wurde widerrufen.",
        "expired_key_error": "Dieses Abonnement ist abgelaufen.",
        "session_limit_error": (
            "Diese Bestellung hat ihr Limit aktiver Sitzungen erreicht."
        ),
        "ip_limit_error": (
            "Diese Bestellung hat ihr Limit verschiedener IP-Adressen erreicht."
        ),
        "portal_not_configured": "Das Portal ist nicht konfiguriert",
        "enter_key_first": "Gib zuerst deinen Zugangsschlüssel ein",
        "access_ended": "Dein Zugang ist abgelaufen oder wurde widerrufen",
    },
    "it": {
        "page_title": "Accesso 2FA temporaneo",
        "language": "Lingua",
        "apply": "Applica",
        "lock_portal": "Blocca portale",
        "access_key_required": "Chiave di accesso richiesta",
        "copy_current_code": "Copia il codice attuale",
        "tap_to_copy": "Tocca per copiare",
        "loading_code": "Caricamento codice…",
        "purchase_accepted": (
            "La chiave di acquisto è stata accettata. Viene mostrato solo il "
            "codice di autenticazione attuale; il segreto TOTP permanente non "
            "viene mai inviato al browser."
        ),
        "provider": "Fornitore",
        "login_email": "E-mail di accesso",
        "expires": "Scade",
        "refresh": "Aggiornamento",
        "seconds": "secondi",
        "enter_access_key": "Inserisci la chiave di accesso",
        "unlock_intro": (
            "Usa la chiave temporanea fornita con l’ordine G2G. Smetterà "
            "automaticamente di funzionare al termine dell’abbonamento."
        ),
        "temporary_access_key": "Chiave di accesso temporanea",
        "open_authenticator": "Apri autenticatore",
        "how_it_works": "Come funziona",
        "how_it_works_body": (
            "La chiave di accesso è collegata all’acquisto e alla data di scadenza. "
            "Dopo l’accettazione, questa pagina fornisce il codice attuale "
            "dell’account software condiviso."
        ),
        "delivery": "Consegna",
        "g2g_order": "Ordine G2G",
        "expiration": "Scadenza",
        "automatic": "Automatica",
        "new_code_in": "Nuovo codice tra",
        "second": "secondo",
        "seconds_unit": "secondi",
        "refreshing": "Aggiornamento",
        "unable_to_retrieve": "Impossibile recuperare il codice.",
        "connection_error": "Errore di connessione.",
        "copied": "Copiato",
        "copy_failed": "Copia non riuscita. Seleziona il codice manualmente.",
        "complete_key_error": (
            "Inserisci la chiave di accesso completa fornita con l’ordine."
        ),
        "rate_limit_error": ("Troppi tentativi non riusciti. Attendi qualche minuto."),
        "invalid_key_error": "Chiave di accesso non valida.",
        "revoked_key_error": "Questa chiave di accesso è stata revocata.",
        "expired_key_error": "Questo abbonamento è scaduto.",
        "session_limit_error": (
            "Questo ordine ha raggiunto il limite di sessioni attive."
        ),
        "ip_limit_error": (
            "Questo ordine ha raggiunto il limite di indirizzi IP distinti."
        ),
        "portal_not_configured": "Il portale non è configurato",
        "enter_key_first": "Inserisci prima la chiave di accesso",
        "access_ended": "Il tuo accesso è scaduto o è stato revocato",
    },
    "pt": {
        "page_title": "Acesso 2FA temporário",
        "language": "Idioma",
        "apply": "Aplicar",
        "lock_portal": "Bloquear portal",
        "access_key_required": "Chave de acesso necessária",
        "copy_current_code": "Copiar código atual",
        "tap_to_copy": "Toque para copiar",
        "loading_code": "Carregando código…",
        "purchase_accepted": (
            "Sua chave de compra foi aceita. Apenas o código de autenticação atual "
            "é exibido; o segredo TOTP permanente nunca é enviado ao navegador."
        ),
        "provider": "Provedor",
        "login_email": "E-mail de login",
        "expires": "Expira",
        "refresh": "Atualização",
        "seconds": "segundos",
        "enter_access_key": "Digite sua chave de acesso",
        "unlock_intro": (
            "Use a chave temporária fornecida com seu pedido G2G. Ela deixará de "
            "funcionar automaticamente quando sua assinatura terminar."
        ),
        "temporary_access_key": "Chave de acesso temporária",
        "open_authenticator": "Abrir autenticador",
        "how_it_works": "Como funciona",
        "how_it_works_body": (
            "A chave de acesso está vinculada à sua compra e ao prazo de validade. "
            "Depois de aceita, esta página fornece o código atual da conta de "
            "software compartilhada."
        ),
        "delivery": "Entrega",
        "g2g_order": "Pedido G2G",
        "expiration": "Validade",
        "automatic": "Automática",
        "new_code_in": "Novo código em",
        "second": "segundo",
        "seconds_unit": "segundos",
        "refreshing": "Atualizando",
        "unable_to_retrieve": "Não foi possível obter o código.",
        "connection_error": "Erro de conexão.",
        "copied": "Copiado",
        "copy_failed": "Falha ao copiar. Selecione o código manualmente.",
        "complete_key_error": (
            "Digite a chave de acesso completa fornecida com seu pedido."
        ),
        "rate_limit_error": ("Muitas tentativas falharam. Aguarde alguns minutos."),
        "invalid_key_error": "Chave de acesso inválida.",
        "revoked_key_error": "Esta chave de acesso foi revogada.",
        "expired_key_error": "Esta assinatura expirou.",
        "session_limit_error": ("Este pedido atingiu o limite de sessões ativas."),
        "ip_limit_error": ("Este pedido atingiu o limite de endereços IP distintos."),
        "portal_not_configured": "O portal não está configurado",
        "enter_key_first": "Digite primeiro sua chave de acesso",
        "access_ended": "Seu acesso expirou ou foi revogado",
    },
    "nl": {
        "page_title": "Tijdelijke 2FA-toegang",
        "language": "Taal",
        "apply": "Toepassen",
        "lock_portal": "Portaal vergrendelen",
        "access_key_required": "Toegangssleutel vereist",
        "copy_current_code": "Huidige code kopiëren",
        "tap_to_copy": "Tik om te kopiëren",
        "loading_code": "Code laden…",
        "purchase_accepted": (
            "Je aankoopsleutel is geaccepteerd. Alleen de huidige "
            "authenticatiecode wordt getoond; het permanente TOTP-geheim wordt "
            "nooit naar de browser verzonden."
        ),
        "provider": "Aanbieder",
        "login_email": "E-mailadres voor aanmelden",
        "expires": "Verloopt",
        "refresh": "Vernieuwen",
        "seconds": "seconden",
        "enter_access_key": "Voer je toegangssleutel in",
        "unlock_intro": (
            "Gebruik de tijdelijke sleutel die bij je G2G-bestelling is geleverd. "
            "Deze stopt automatisch wanneer je abonnement afloopt."
        ),
        "temporary_access_key": "Tijdelijke toegangssleutel",
        "open_authenticator": "Authenticator openen",
        "how_it_works": "Hoe het werkt",
        "how_it_works_body": (
            "De toegangssleutel is gekoppeld aan je aankoop en vervaldatum. Na "
            "acceptatie toont deze pagina de huidige code voor het gedeelde "
            "softwareaccount."
        ),
        "delivery": "Levering",
        "g2g_order": "G2G-bestelling",
        "expiration": "Vervaldatum",
        "automatic": "Automatisch",
        "new_code_in": "Nieuwe code over",
        "second": "seconde",
        "seconds_unit": "seconden",
        "refreshing": "Vernieuwen",
        "unable_to_retrieve": "Kan de code niet ophalen.",
        "connection_error": "Verbindingsfout.",
        "copied": "Gekopieerd",
        "copy_failed": "Kopiëren mislukt. Selecteer de code handmatig.",
        "complete_key_error": (
            "Voer de volledige toegangssleutel uit je bestelling in."
        ),
        "rate_limit_error": ("Te veel mislukte pogingen. Wacht enkele minuten."),
        "invalid_key_error": "Ongeldige toegangssleutel.",
        "revoked_key_error": "Deze toegangssleutel is ingetrokken.",
        "expired_key_error": "Dit abonnement is verlopen.",
        "session_limit_error": (
            "Deze bestelling heeft de limiet voor actieve sessies bereikt."
        ),
        "ip_limit_error": (
            "Deze bestelling heeft de limiet voor verschillende IP-adressen bereikt."
        ),
        "portal_not_configured": "Het portaal is niet geconfigureerd",
        "enter_key_first": "Voer eerst je toegangssleutel in",
        "access_ended": "Je toegang is verlopen of ingetrokken",
    },
    "pl": {
        "page_title": "Tymczasowy dostęp 2FA",
        "language": "Język",
        "apply": "Zastosuj",
        "lock_portal": "Zablokuj portal",
        "access_key_required": "Wymagany klucz dostępu",
        "copy_current_code": "Kopiuj bieżący kod",
        "tap_to_copy": "Dotknij, aby skopiować",
        "loading_code": "Ładowanie kodu…",
        "purchase_accepted": (
            "Twój klucz zakupu został zaakceptowany. Wyświetlany jest tylko bieżący "
            "kod uwierzytelniający; stały sekret TOTP nigdy nie jest wysyłany do "
            "przeglądarki."
        ),
        "provider": "Dostawca",
        "login_email": "E-mail logowania",
        "expires": "Wygasa",
        "refresh": "Odświeżanie",
        "seconds": "sekund",
        "enter_access_key": "Wprowadź klucz dostępu",
        "unlock_intro": (
            "Użyj tymczasowego klucza dostarczonego z zamówieniem G2G. Przestanie "
            "działać automatycznie po zakończeniu subskrypcji."
        ),
        "temporary_access_key": "Tymczasowy klucz dostępu",
        "open_authenticator": "Otwórz uwierzytelniacz",
        "how_it_works": "Jak to działa",
        "how_it_works_body": (
            "Klucz dostępu jest powiązany z zakupem i datą wygaśnięcia. Po jego "
            "zaakceptowaniu strona udostępnia bieżący kod do współdzielonego konta."
        ),
        "delivery": "Dostawa",
        "g2g_order": "Zamówienie G2G",
        "expiration": "Wygaśnięcie",
        "automatic": "Automatyczne",
        "new_code_in": "Nowy kod za",
        "second": "sekundę",
        "seconds_unit": "sekund",
        "refreshing": "Odświeżanie",
        "unable_to_retrieve": "Nie można pobrać kodu.",
        "connection_error": "Błąd połączenia.",
        "copied": "Skopiowano",
        "copy_failed": "Kopiowanie nie powiodło się. Zaznacz kod ręcznie.",
        "complete_key_error": (
            "Wprowadź pełny klucz dostępu dostarczony z zamówieniem."
        ),
        "rate_limit_error": ("Zbyt wiele nieudanych prób. Poczekaj kilka minut."),
        "invalid_key_error": "Nieprawidłowy klucz dostępu.",
        "revoked_key_error": "Ten klucz dostępu został unieważniony.",
        "expired_key_error": "Ta subskrypcja wygasła.",
        "session_limit_error": ("To zamówienie osiągnęło limit aktywnych sesji."),
        "ip_limit_error": ("To zamówienie osiągnęło limit różnych adresów IP."),
        "portal_not_configured": "Portal nie jest skonfigurowany",
        "enter_key_first": "Najpierw wprowadź klucz dostępu",
        "access_ended": "Twój dostęp wygasł lub został unieważniony",
    },
    "tr": {
        "page_title": "Geçici 2FA Erişimi",
        "language": "Dil",
        "apply": "Uygula",
        "lock_portal": "Portalı kilitle",
        "access_key_required": "Erişim anahtarı gerekli",
        "copy_current_code": "Geçerli kodu kopyala",
        "tap_to_copy": "Kopyalamak için dokunun",
        "loading_code": "Kod yükleniyor…",
        "purchase_accepted": (
            "Satın alma anahtarınız kabul edildi. Yalnızca geçerli doğrulama kodu "
            "gösterilir; kalıcı TOTP sırrı tarayıcıya hiçbir zaman gönderilmez."
        ),
        "provider": "Sağlayıcı",
        "login_email": "Giriş e-postası",
        "expires": "Bitiş",
        "refresh": "Yenileme",
        "seconds": "saniye",
        "enter_access_key": "Erişim anahtarınızı girin",
        "unlock_intro": (
            "G2G siparişinizle verilen geçici anahtarı kullanın. Aboneliğiniz "
            "bittiğinde otomatik olarak çalışmayı durdurur."
        ),
        "temporary_access_key": "Geçici erişim anahtarı",
        "open_authenticator": "Doğrulayıcıyı aç",
        "how_it_works": "Nasıl çalışır",
        "how_it_works_body": (
            "Erişim anahtarı satın alma ve sona erme tarihinize bağlıdır. Kabul "
            "edildikten sonra bu sayfa paylaşılan yazılım hesabının geçerli kodunu "
            "sağlar."
        ),
        "delivery": "Teslimat",
        "g2g_order": "G2G siparişi",
        "expiration": "Sona erme",
        "automatic": "Otomatik",
        "new_code_in": "Yeni koda kalan",
        "second": "saniye",
        "seconds_unit": "saniye",
        "refreshing": "Yenileniyor",
        "unable_to_retrieve": "Kod alınamadı.",
        "connection_error": "Bağlantı hatası.",
        "copied": "Kopyalandı",
        "copy_failed": "Kopyalama başarısız. Kodu elle seçin.",
        "complete_key_error": (
            "Siparişinizle verilen erişim anahtarının tamamını girin."
        ),
        "rate_limit_error": ("Çok fazla başarısız deneme. Birkaç dakika bekleyin."),
        "invalid_key_error": "Geçersiz erişim anahtarı.",
        "revoked_key_error": "Bu erişim anahtarı iptal edildi.",
        "expired_key_error": "Bu aboneliğin süresi doldu.",
        "session_limit_error": ("Bu sipariş etkin oturum sınırına ulaştı."),
        "ip_limit_error": ("Bu sipariş farklı IP adresi sınırına ulaştı."),
        "portal_not_configured": "Portal yapılandırılmamış",
        "enter_key_first": "Önce erişim anahtarınızı girin",
        "access_ended": "Erişiminizin süresi doldu veya iptal edildi",
    },
    "ru": {
        "page_title": "Временный доступ 2FA",
        "language": "Язык",
        "apply": "Применить",
        "lock_portal": "Заблокировать портал",
        "access_key_required": "Требуется ключ доступа",
        "copy_current_code": "Копировать текущий код",
        "tap_to_copy": "Нажмите, чтобы скопировать",
        "loading_code": "Загрузка кода…",
        "purchase_accepted": (
            "Ваш ключ покупки принят. Отображается только текущий код "
            "аутентификации; постоянный секрет TOTP никогда не отправляется в "
            "браузер."
        ),
        "provider": "Поставщик",
        "login_email": "Электронная почта для входа",
        "expires": "Истекает",
        "refresh": "Обновление",
        "seconds": "секунд",
        "enter_access_key": "Введите ключ доступа",
        "unlock_intro": (
            "Используйте временный ключ из заказа G2G. Он автоматически перестанет "
            "работать после окончания подписки."
        ),
        "temporary_access_key": "Временный ключ доступа",
        "open_authenticator": "Открыть аутентификатор",
        "how_it_works": "Как это работает",
        "how_it_works_body": (
            "Ключ доступа связан с покупкой и сроком действия. После его принятия "
            "эта страница предоставляет текущий код общей учётной записи."
        ),
        "delivery": "Доставка",
        "g2g_order": "Заказ G2G",
        "expiration": "Срок действия",
        "automatic": "Автоматически",
        "new_code_in": "Новый код через",
        "second": "секунду",
        "seconds_unit": "секунд",
        "refreshing": "Обновление",
        "unable_to_retrieve": "Не удалось получить код.",
        "connection_error": "Ошибка соединения.",
        "copied": "Скопировано",
        "copy_failed": "Не удалось скопировать. Выберите код вручную.",
        "complete_key_error": (
            "Введите полный ключ доступа, предоставленный с заказом."
        ),
        "rate_limit_error": (
            "Слишком много неудачных попыток. Подождите несколько минут."
        ),
        "invalid_key_error": "Неверный ключ доступа.",
        "revoked_key_error": "Этот ключ доступа был отозван.",
        "expired_key_error": "Срок действия подписки истёк.",
        "session_limit_error": ("Для этого заказа достигнут лимит активных сеансов."),
        "ip_limit_error": ("Для этого заказа достигнут лимит различных IP-адресов."),
        "portal_not_configured": "Портал не настроен",
        "enter_key_first": "Сначала введите ключ доступа",
        "access_ended": "Ваш доступ истёк или был отозван",
    },
    "uk": {
        "page_title": "Тимчасовий доступ 2FA",
        "language": "Мова",
        "apply": "Застосувати",
        "lock_portal": "Заблокувати портал",
        "access_key_required": "Потрібен ключ доступу",
        "copy_current_code": "Копіювати поточний код",
        "tap_to_copy": "Натисніть, щоб скопіювати",
        "loading_code": "Завантаження коду…",
        "purchase_accepted": (
            "Ваш ключ покупки прийнято. Відображається лише поточний код "
            "автентифікації; постійний секрет TOTP ніколи не надсилається браузеру."
        ),
        "provider": "Постачальник",
        "login_email": "Електронна пошта для входу",
        "expires": "Закінчується",
        "refresh": "Оновлення",
        "seconds": "секунд",
        "enter_access_key": "Введіть ключ доступу",
        "unlock_intro": (
            "Використайте тимчасовий ключ із замовлення G2G. Він автоматично "
            "припинить працювати після завершення підписки."
        ),
        "temporary_access_key": "Тимчасовий ключ доступу",
        "open_authenticator": "Відкрити автентифікатор",
        "how_it_works": "Як це працює",
        "how_it_works_body": (
            "Ключ доступу пов’язаний із покупкою та строком дії. Після прийняття "
            "ця сторінка надає поточний код спільного облікового запису."
        ),
        "delivery": "Доставка",
        "g2g_order": "Замовлення G2G",
        "expiration": "Строк дії",
        "automatic": "Автоматично",
        "new_code_in": "Новий код через",
        "second": "секунду",
        "seconds_unit": "секунд",
        "refreshing": "Оновлення",
        "unable_to_retrieve": "Не вдалося отримати код.",
        "connection_error": "Помилка з’єднання.",
        "copied": "Скопійовано",
        "copy_failed": "Не вдалося скопіювати. Виберіть код вручну.",
        "complete_key_error": ("Введіть повний ключ доступу, наданий із замовленням."),
        "rate_limit_error": ("Забагато невдалих спроб. Зачекайте кілька хвилин."),
        "invalid_key_error": "Недійсний ключ доступу.",
        "revoked_key_error": "Цей ключ доступу було відкликано.",
        "expired_key_error": "Строк дії цієї підписки закінчився.",
        "session_limit_error": (
            "Для цього замовлення досягнуто ліміт активних сеансів."
        ),
        "ip_limit_error": ("Для цього замовлення досягнуто ліміт різних IP-адрес."),
        "portal_not_configured": "Портал не налаштовано",
        "enter_key_first": "Спочатку введіть ключ доступу",
        "access_ended": "Ваш доступ закінчився або був відкликаний",
    },
    "ar": {
        "page_title": "وصول مؤقت بالمصادقة الثنائية",
        "language": "اللغة",
        "apply": "تطبيق",
        "lock_portal": "قفل البوابة",
        "access_key_required": "مفتاح الوصول مطلوب",
        "copy_current_code": "نسخ الرمز الحالي",
        "tap_to_copy": "اضغط للنسخ",
        "loading_code": "جارٍ تحميل الرمز…",
        "purchase_accepted": (
            "تم قبول مفتاح الشراء. يُعرض رمز المصادقة الحالي فقط؛ ولا يتم إرسال "
            "سر TOTP الدائم إلى المتصفح مطلقًا."
        ),
        "provider": "المزوّد",
        "login_email": "بريد تسجيل الدخول",
        "expires": "ينتهي",
        "refresh": "التحديث",
        "seconds": "ثانية",
        "enter_access_key": "أدخل مفتاح الوصول",
        "unlock_intro": (
            "استخدم المفتاح المؤقت المرفق بطلب G2G. سيتوقف عن العمل تلقائيًا عند "
            "انتهاء اشتراكك."
        ),
        "temporary_access_key": "مفتاح وصول مؤقت",
        "open_authenticator": "فتح تطبيق المصادقة",
        "how_it_works": "كيف يعمل",
        "how_it_works_body": (
            "يرتبط مفتاح الوصول بعملية الشراء ووقت انتهاء الصلاحية. بعد قبوله، "
            "توفّر هذه الصفحة الرمز الحالي لحساب البرنامج المشترك."
        ),
        "delivery": "التسليم",
        "g2g_order": "طلب G2G",
        "expiration": "انتهاء الصلاحية",
        "automatic": "تلقائي",
        "new_code_in": "رمز جديد خلال",
        "second": "ثانية",
        "seconds_unit": "ثانية",
        "refreshing": "جارٍ التحديث",
        "unable_to_retrieve": "تعذّر استرداد الرمز.",
        "connection_error": "خطأ في الاتصال.",
        "copied": "تم النسخ",
        "copy_failed": "فشل النسخ. حدّد الرمز يدويًا.",
        "complete_key_error": "أدخل مفتاح الوصول الكامل المرفق بطلبك.",
        "rate_limit_error": "محاولات فاشلة كثيرة. انتظر بضع دقائق.",
        "invalid_key_error": "مفتاح الوصول غير صالح.",
        "revoked_key_error": "تم إلغاء مفتاح الوصول هذا.",
        "expired_key_error": "انتهت صلاحية هذا الاشتراك.",
        "session_limit_error": "وصل هذا الطلب إلى حد الجلسات النشطة.",
        "ip_limit_error": "وصل هذا الطلب إلى حد عناوين IP المختلفة.",
        "portal_not_configured": "البوابة غير مهيأة",
        "enter_key_first": "أدخل مفتاح الوصول أولًا",
        "access_ended": "انتهى وصولك أو تم إلغاؤه",
    },
    "hi": {
        "page_title": "अस्थायी 2FA एक्सेस",
        "language": "भाषा",
        "apply": "लागू करें",
        "lock_portal": "पोर्टल लॉक करें",
        "access_key_required": "एक्सेस कुंजी आवश्यक है",
        "copy_current_code": "वर्तमान कोड कॉपी करें",
        "tap_to_copy": "कॉपी करने के लिए टैप करें",
        "loading_code": "कोड लोड हो रहा है…",
        "purchase_accepted": (
            "आपकी खरीद कुंजी स्वीकार कर ली गई है। केवल वर्तमान प्रमाणीकरण कोड "
            "दिखाया जाता है; स्थायी TOTP सीक्रेट ब्राउज़र को कभी नहीं भेजा जाता।"
        ),
        "provider": "प्रदाता",
        "login_email": "लॉगिन ईमेल",
        "expires": "समाप्ति",
        "refresh": "रीफ़्रेश",
        "seconds": "सेकंड",
        "enter_access_key": "अपनी एक्सेस कुंजी दर्ज करें",
        "unlock_intro": (
            "अपने G2G ऑर्डर के साथ मिली अस्थायी कुंजी का उपयोग करें। सदस्यता समाप्त "
            "होने पर यह अपने आप काम करना बंद कर देगी।"
        ),
        "temporary_access_key": "अस्थायी एक्सेस कुंजी",
        "open_authenticator": "ऑथेंटिकेटर खोलें",
        "how_it_works": "यह कैसे काम करता है",
        "how_it_works_body": (
            "एक्सेस कुंजी आपकी खरीद और समाप्ति समय से जुड़ी है। स्वीकार होने के "
            "बाद यह पेज साझा सॉफ़्टवेयर खाते का वर्तमान कोड देता है।"
        ),
        "delivery": "डिलीवरी",
        "g2g_order": "G2G ऑर्डर",
        "expiration": "समाप्ति",
        "automatic": "स्वचालित",
        "new_code_in": "नया कोड",
        "second": "सेकंड में",
        "seconds_unit": "सेकंड में",
        "refreshing": "रीफ़्रेश हो रहा है",
        "unable_to_retrieve": "कोड प्राप्त नहीं किया जा सका।",
        "connection_error": "कनेक्शन त्रुटि।",
        "copied": "कॉपी किया गया",
        "copy_failed": "कॉपी विफल। कोड को मैन्युअल रूप से चुनें।",
        "complete_key_error": ("अपने ऑर्डर के साथ मिली पूरी एक्सेस कुंजी दर्ज करें।"),
        "rate_limit_error": ("बहुत अधिक असफल प्रयास। कुछ मिनट प्रतीक्षा करें।"),
        "invalid_key_error": "अमान्य एक्सेस कुंजी।",
        "revoked_key_error": "यह एक्सेस कुंजी रद्द कर दी गई है।",
        "expired_key_error": "यह सदस्यता समाप्त हो गई है।",
        "session_limit_error": "इस ऑर्डर की सक्रिय सत्र सीमा पूरी हो गई है।",
        "ip_limit_error": "इस ऑर्डर की अलग IP पतों की सीमा पूरी हो गई है।",
        "portal_not_configured": "पोर्टल कॉन्फ़िगर नहीं है",
        "enter_key_first": "पहले अपनी एक्सेस कुंजी दर्ज करें",
        "access_ended": "आपका एक्सेस समाप्त हो गया है या रद्द किया गया है",
    },
    "zh-cn": {
        "page_title": "临时双重验证访问",
        "language": "语言",
        "apply": "应用",
        "lock_portal": "锁定门户",
        "access_key_required": "需要访问密钥",
        "copy_current_code": "复制当前验证码",
        "tap_to_copy": "点击复制",
        "loading_code": "正在加载验证码…",
        "purchase_accepted": (
            "您的购买密钥已被接受。这里只显示当前验证码；永久 TOTP 密钥绝不会发送"
            "到浏览器。"
        ),
        "provider": "服务商",
        "login_email": "登录邮箱",
        "expires": "到期时间",
        "refresh": "刷新",
        "seconds": "秒",
        "enter_access_key": "请输入访问密钥",
        "unlock_intro": (
            "请使用 G2G 订单中提供的临时密钥。订阅结束后，该密钥将自动停止工作。"
        ),
        "temporary_access_key": "临时访问密钥",
        "open_authenticator": "打开验证器",
        "how_it_works": "使用说明",
        "how_it_works_body": (
            "访问密钥与您的购买和到期时间关联。密钥验证通过后，本页面会提供共享"
            "软件账户的当前验证码。"
        ),
        "delivery": "交付",
        "g2g_order": "G2G 订单",
        "expiration": "到期",
        "automatic": "自动",
        "new_code_in": "新验证码将在",
        "second": "秒后生成",
        "seconds_unit": "秒后生成",
        "refreshing": "正在刷新",
        "unable_to_retrieve": "无法获取验证码。",
        "connection_error": "连接错误。",
        "copied": "已复制",
        "copy_failed": "复制失败，请手动选择验证码。",
        "complete_key_error": "请输入订单中提供的完整访问密钥。",
        "rate_limit_error": "失败次数过多，请等待几分钟。",
        "invalid_key_error": "访问密钥无效。",
        "revoked_key_error": "此访问密钥已被撤销。",
        "expired_key_error": "此订阅已过期。",
        "session_limit_error": "此订单已达到活动会话数量上限。",
        "ip_limit_error": "此订单已达到不同 IP 地址数量上限。",
        "portal_not_configured": "门户尚未配置",
        "enter_key_first": "请先输入访问密钥",
        "access_ended": "您的访问权限已过期或被撤销",
    },
    "zh-tw": {
        "page_title": "臨時雙重驗證存取",
        "language": "語言",
        "apply": "套用",
        "lock_portal": "鎖定入口",
        "access_key_required": "需要存取金鑰",
        "copy_current_code": "複製目前驗證碼",
        "tap_to_copy": "點擊複製",
        "loading_code": "正在載入驗證碼…",
        "purchase_accepted": (
            "您的購買金鑰已被接受。此處只顯示目前驗證碼；永久 TOTP 密鑰絕不會"
            "傳送至瀏覽器。"
        ),
        "provider": "服務商",
        "login_email": "登入電子郵件",
        "expires": "到期時間",
        "refresh": "重新整理",
        "seconds": "秒",
        "enter_access_key": "請輸入存取金鑰",
        "unlock_intro": (
            "請使用 G2G 訂單中提供的臨時金鑰。訂閱結束後，金鑰將自動停止運作。"
        ),
        "temporary_access_key": "臨時存取金鑰",
        "open_authenticator": "開啟驗證器",
        "how_it_works": "使用方式",
        "how_it_works_body": (
            "存取金鑰與您的購買及到期時間相關聯。金鑰通過驗證後，此頁面會提供"
            "共用軟體帳戶的目前驗證碼。"
        ),
        "delivery": "交付",
        "g2g_order": "G2G 訂單",
        "expiration": "到期",
        "automatic": "自動",
        "new_code_in": "新驗證碼將在",
        "second": "秒後產生",
        "seconds_unit": "秒後產生",
        "refreshing": "正在重新整理",
        "unable_to_retrieve": "無法取得驗證碼。",
        "connection_error": "連線錯誤。",
        "copied": "已複製",
        "copy_failed": "複製失敗，請手動選取驗證碼。",
        "complete_key_error": "請輸入訂單中提供的完整存取金鑰。",
        "rate_limit_error": "失敗次數過多，請等待幾分鐘。",
        "invalid_key_error": "存取金鑰無效。",
        "revoked_key_error": "此存取金鑰已被撤銷。",
        "expired_key_error": "此訂閱已過期。",
        "session_limit_error": "此訂單已達到活動工作階段數量上限。",
        "ip_limit_error": "此訂單已達到不同 IP 位址數量上限。",
        "portal_not_configured": "入口尚未設定",
        "enter_key_first": "請先輸入存取金鑰",
        "access_ended": "您的存取權已過期或被撤銷",
    },
    "ja": {
        "page_title": "一時的な2FAアクセス",
        "language": "言語",
        "apply": "適用",
        "lock_portal": "ポータルをロック",
        "access_key_required": "アクセスキーが必要です",
        "copy_current_code": "現在のコードをコピー",
        "tap_to_copy": "タップしてコピー",
        "loading_code": "コードを読み込み中…",
        "purchase_accepted": (
            "購入キーが承認されました。現在の認証コードのみが表示され、永続的な"
            "TOTPシークレットがブラウザーに送信されることはありません。"
        ),
        "provider": "プロバイダー",
        "login_email": "ログインメール",
        "expires": "有効期限",
        "refresh": "更新",
        "seconds": "秒",
        "enter_access_key": "アクセスキーを入力",
        "unlock_intro": (
            "G2G注文で提供された一時キーを使用してください。サブスクリプション"
            "終了時に自動的に使用できなくなります。"
        ),
        "temporary_access_key": "一時アクセスキー",
        "open_authenticator": "認証画面を開く",
        "how_it_works": "仕組み",
        "how_it_works_body": (
            "アクセスキーは購入と有効期限に関連付けられています。承認されると、"
            "このページに共有ソフトウェアアカウントの現在のコードが表示されます。"
        ),
        "delivery": "配信",
        "g2g_order": "G2G注文",
        "expiration": "有効期限",
        "automatic": "自動",
        "new_code_in": "新しいコードまで",
        "second": "秒",
        "seconds_unit": "秒",
        "refreshing": "更新中",
        "unable_to_retrieve": "コードを取得できません。",
        "connection_error": "接続エラー。",
        "copied": "コピーしました",
        "copy_failed": "コピーに失敗しました。コードを手動で選択してください。",
        "complete_key_error": "注文で提供された完全なアクセスキーを入力してください。",
        "rate_limit_error": "失敗回数が多すぎます。数分待ってください。",
        "invalid_key_error": "アクセスキーが無効です。",
        "revoked_key_error": "このアクセスキーは取り消されました。",
        "expired_key_error": "このサブスクリプションは期限切れです。",
        "session_limit_error": "この注文はアクティブセッションの上限に達しました。",
        "ip_limit_error": "この注文は異なるIPアドレス数の上限に達しました。",
        "portal_not_configured": "ポータルが設定されていません",
        "enter_key_first": "最初にアクセスキーを入力してください",
        "access_ended": "アクセスの期限が切れたか、取り消されました",
    },
    "ko": {
        "page_title": "임시 2단계 인증 액세스",
        "language": "언어",
        "apply": "적용",
        "lock_portal": "포털 잠금",
        "access_key_required": "액세스 키 필요",
        "copy_current_code": "현재 코드 복사",
        "tap_to_copy": "탭하여 복사",
        "loading_code": "코드 불러오는 중…",
        "purchase_accepted": (
            "구매 키가 승인되었습니다. 현재 인증 코드만 표시되며 영구 TOTP 비밀 키는 "
            "브라우저로 전송되지 않습니다."
        ),
        "provider": "제공업체",
        "login_email": "로그인 이메일",
        "expires": "만료",
        "refresh": "새로 고침",
        "seconds": "초",
        "enter_access_key": "액세스 키 입력",
        "unlock_intro": (
            "G2G 주문과 함께 제공된 임시 키를 사용하세요. 구독이 종료되면 자동으로 "
            "작동을 멈춥니다."
        ),
        "temporary_access_key": "임시 액세스 키",
        "open_authenticator": "인증 화면 열기",
        "how_it_works": "작동 방식",
        "how_it_works_body": (
            "액세스 키는 구매 및 만료 시간과 연결됩니다. 승인되면 이 페이지에서 공유 "
            "소프트웨어 계정의 현재 코드를 제공합니다."
        ),
        "delivery": "배송",
        "g2g_order": "G2G 주문",
        "expiration": "만료",
        "automatic": "자동",
        "new_code_in": "새 코드까지",
        "second": "초",
        "seconds_unit": "초",
        "refreshing": "새로 고치는 중",
        "unable_to_retrieve": "코드를 가져올 수 없습니다.",
        "connection_error": "연결 오류.",
        "copied": "복사됨",
        "copy_failed": "복사에 실패했습니다. 코드를 직접 선택하세요.",
        "complete_key_error": "주문과 함께 제공된 전체 액세스 키를 입력하세요.",
        "rate_limit_error": "실패한 시도가 너무 많습니다. 잠시 기다리세요.",
        "invalid_key_error": "유효하지 않은 액세스 키입니다.",
        "revoked_key_error": "이 액세스 키는 취소되었습니다.",
        "expired_key_error": "이 구독은 만료되었습니다.",
        "session_limit_error": "이 주문은 활성 세션 한도에 도달했습니다.",
        "ip_limit_error": "이 주문은 서로 다른 IP 주소 한도에 도달했습니다.",
        "portal_not_configured": "포털이 설정되지 않았습니다",
        "enter_key_first": "먼저 액세스 키를 입력하세요",
        "access_ended": "액세스가 만료되었거나 취소되었습니다",
    },
    "id": {
        "page_title": "Akses 2FA Sementara",
        "language": "Bahasa",
        "apply": "Terapkan",
        "lock_portal": "Kunci portal",
        "access_key_required": "Kunci akses diperlukan",
        "copy_current_code": "Salin kode saat ini",
        "tap_to_copy": "Ketuk untuk menyalin",
        "loading_code": "Memuat kode…",
        "purchase_accepted": (
            "Kunci pembelian Anda telah diterima. Hanya kode autentikasi saat ini "
            "yang ditampilkan; rahasia TOTP permanen tidak pernah dikirim ke browser."
        ),
        "provider": "Penyedia",
        "login_email": "Email masuk",
        "expires": "Berakhir",
        "refresh": "Penyegaran",
        "seconds": "detik",
        "enter_access_key": "Masukkan kunci akses Anda",
        "unlock_intro": (
            "Gunakan kunci sementara yang dikirim bersama pesanan G2G Anda. Kunci "
            "akan berhenti berfungsi otomatis saat langganan berakhir."
        ),
        "temporary_access_key": "Kunci akses sementara",
        "open_authenticator": "Buka autentikator",
        "how_it_works": "Cara kerja",
        "how_it_works_body": (
            "Kunci akses ditautkan ke pembelian dan waktu kedaluwarsa Anda. Setelah "
            "diterima, halaman ini memberikan kode saat ini untuk akun perangkat "
            "lunak bersama."
        ),
        "delivery": "Pengiriman",
        "g2g_order": "Pesanan G2G",
        "expiration": "Kedaluwarsa",
        "automatic": "Otomatis",
        "new_code_in": "Kode baru dalam",
        "second": "detik",
        "seconds_unit": "detik",
        "refreshing": "Menyegarkan",
        "unable_to_retrieve": "Tidak dapat mengambil kode.",
        "connection_error": "Kesalahan koneksi.",
        "copied": "Disalin",
        "copy_failed": "Gagal menyalin. Pilih kode secara manual.",
        "complete_key_error": (
            "Masukkan kunci akses lengkap yang diberikan bersama pesanan Anda."
        ),
        "rate_limit_error": ("Terlalu banyak percobaan gagal. Tunggu beberapa menit."),
        "invalid_key_error": "Kunci akses tidak valid.",
        "revoked_key_error": "Kunci akses ini telah dicabut.",
        "expired_key_error": "Langganan ini telah berakhir.",
        "session_limit_error": ("Pesanan ini telah mencapai batas sesi aktif."),
        "ip_limit_error": ("Pesanan ini telah mencapai batas alamat IP yang berbeda."),
        "portal_not_configured": "Portal belum dikonfigurasi",
        "enter_key_first": "Masukkan kunci akses Anda terlebih dahulu",
        "access_ended": "Akses Anda telah berakhir atau dicabut",
    },
    "vi": {
        "page_title": "Truy cập 2FA tạm thời",
        "language": "Ngôn ngữ",
        "apply": "Áp dụng",
        "lock_portal": "Khóa cổng",
        "access_key_required": "Cần có khóa truy cập",
        "copy_current_code": "Sao chép mã hiện tại",
        "tap_to_copy": "Nhấn để sao chép",
        "loading_code": "Đang tải mã…",
        "purchase_accepted": (
            "Khóa mua hàng của bạn đã được chấp nhận. Chỉ mã xác thực hiện tại "
            "được hiển thị; bí mật TOTP vĩnh viễn không bao giờ được gửi tới "
            "trình duyệt."
        ),
        "provider": "Nhà cung cấp",
        "login_email": "Email đăng nhập",
        "expires": "Hết hạn",
        "refresh": "Làm mới",
        "seconds": "giây",
        "enter_access_key": "Nhập khóa truy cập của bạn",
        "unlock_intro": (
            "Sử dụng khóa tạm thời được cung cấp cùng đơn hàng G2G. Khóa sẽ tự động "
            "ngừng hoạt động khi gói đăng ký kết thúc."
        ),
        "temporary_access_key": "Khóa truy cập tạm thời",
        "open_authenticator": "Mở trình xác thực",
        "how_it_works": "Cách hoạt động",
        "how_it_works_body": (
            "Khóa truy cập được liên kết với giao dịch mua và thời gian hết hạn. "
            "Sau khi được chấp nhận, trang này cung cấp mã hiện tại cho tài khoản "
            "phần mềm dùng chung."
        ),
        "delivery": "Giao hàng",
        "g2g_order": "Đơn hàng G2G",
        "expiration": "Hết hạn",
        "automatic": "Tự động",
        "new_code_in": "Mã mới sau",
        "second": "giây",
        "seconds_unit": "giây",
        "refreshing": "Đang làm mới",
        "unable_to_retrieve": "Không thể lấy mã.",
        "connection_error": "Lỗi kết nối.",
        "copied": "Đã sao chép",
        "copy_failed": "Sao chép thất bại. Hãy chọn mã theo cách thủ công.",
        "complete_key_error": (
            "Nhập đầy đủ khóa truy cập được cung cấp cùng đơn hàng."
        ),
        "rate_limit_error": ("Quá nhiều lần thử thất bại. Hãy đợi vài phút."),
        "invalid_key_error": "Khóa truy cập không hợp lệ.",
        "revoked_key_error": "Khóa truy cập này đã bị thu hồi.",
        "expired_key_error": "Gói đăng ký này đã hết hạn.",
        "session_limit_error": ("Đơn hàng này đã đạt giới hạn phiên đang hoạt động."),
        "ip_limit_error": ("Đơn hàng này đã đạt giới hạn địa chỉ IP khác nhau."),
        "portal_not_configured": "Cổng chưa được cấu hình",
        "enter_key_first": "Hãy nhập khóa truy cập trước",
        "access_ended": "Quyền truy cập đã hết hạn hoặc bị thu hồi",
    },
    "th": {
        "page_title": "การเข้าถึง 2FA ชั่วคราว",
        "language": "ภาษา",
        "apply": "ใช้",
        "lock_portal": "ล็อกพอร์ทัล",
        "access_key_required": "ต้องใช้คีย์การเข้าถึง",
        "copy_current_code": "คัดลอกรหัสปัจจุบัน",
        "tap_to_copy": "แตะเพื่อคัดลอก",
        "loading_code": "กำลังโหลดรหัส…",
        "purchase_accepted": (
            "ยอมรับคีย์การซื้อของคุณแล้ว ระบบจะแสดงเฉพาะรหัสยืนยันตัวตนปัจจุบัน "
            "และจะไม่ส่งข้อมูลลับ TOTP ถาวรไปยังเบราว์เซอร์"
        ),
        "provider": "ผู้ให้บริการ",
        "login_email": "อีเมลเข้าสู่ระบบ",
        "expires": "หมดอายุ",
        "refresh": "รีเฟรช",
        "seconds": "วินาที",
        "enter_access_key": "ป้อนคีย์การเข้าถึงของคุณ",
        "unlock_intro": (
            "ใช้คีย์ชั่วคราวที่ได้รับพร้อมคำสั่งซื้อ G2G คีย์จะหยุดทำงานอัตโนมัติเมื่อการสมัครของคุณสิ้นสุดลง"
        ),
        "temporary_access_key": "คีย์การเข้าถึงชั่วคราว",
        "open_authenticator": "เปิดตัวยืนยันตัวตน",
        "how_it_works": "วิธีการทำงาน",
        "how_it_works_body": (
            "คีย์การเข้าถึงเชื่อมโยงกับการซื้อและเวลาหมดอายุ เมื่อได้รับการยอมรับ "
            "หน้านี้จะแสดงรหัสปัจจุบันของบัญชีซอฟต์แวร์ที่ใช้ร่วมกัน"
        ),
        "delivery": "การจัดส่ง",
        "g2g_order": "คำสั่งซื้อ G2G",
        "expiration": "การหมดอายุ",
        "automatic": "อัตโนมัติ",
        "new_code_in": "รหัสใหม่ใน",
        "second": "วินาที",
        "seconds_unit": "วินาที",
        "refreshing": "กำลังรีเฟรช",
        "unable_to_retrieve": "ไม่สามารถดึงรหัสได้",
        "connection_error": "เกิดข้อผิดพลาดในการเชื่อมต่อ",
        "copied": "คัดลอกแล้ว",
        "copy_failed": "คัดลอกไม่สำเร็จ โปรดเลือกรหัสด้วยตนเอง",
        "complete_key_error": "ป้อนคีย์การเข้าถึงแบบเต็มที่ได้รับพร้อมคำสั่งซื้อ",
        "rate_limit_error": "มีความพยายามที่ล้มเหลวมากเกินไป โปรดรอสักครู่",
        "invalid_key_error": "คีย์การเข้าถึงไม่ถูกต้อง",
        "revoked_key_error": "คีย์การเข้าถึงนี้ถูกเพิกถอนแล้ว",
        "expired_key_error": "การสมัครนี้หมดอายุแล้ว",
        "session_limit_error": "คำสั่งซื้อนี้ถึงขีดจำกัดเซสชันที่ใช้งานอยู่แล้ว",
        "ip_limit_error": "คำสั่งซื้อนี้ถึงขีดจำกัดที่อยู่ IP ที่แตกต่างกันแล้ว",
        "portal_not_configured": "ยังไม่ได้กำหนดค่าพอร์ทัล",
        "enter_key_first": "ป้อนคีย์การเข้าถึงก่อน",
        "access_ended": "การเข้าถึงของคุณหมดอายุหรือถูกเพิกถอนแล้ว",
    },
}

ERROR_TRANSLATION_KEYS = {
    "Too many failed attempts. Wait a few minutes.": "rate_limit_error",
    "Invalid access key.": "invalid_key_error",
    "This access key has been revoked.": "revoked_key_error",
    "This subscription has expired.": "expired_key_error",
    "This order has reached its active-session limit.": "session_limit_error",
    "This order has reached its distinct-IP limit.": "ip_limit_error",
}

LANGUAGE_ALIASES = {
    "zh": "zh-cn",
    "zh-cn": "zh-cn",
    "zh-hans": "zh-cn",
    "zh-sg": "zh-cn",
    "zh-tw": "zh-tw",
    "zh-hant": "zh-tw",
    "zh-hk": "zh-tw",
    "zh-mo": "zh-tw",
}


def supported_language(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("_", "-")
    language_parts = normalized.split("-")
    if language_parts[0] == "zh":
        if any(part in {"hant", "tw", "hk", "mo"} for part in language_parts[1:]):
            return "zh-tw"
        return "zh-cn"
    if normalized in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[normalized]
    if normalized in TRANSLATION_OVERRIDES or normalized == DEFAULT_LANGUAGE:
        return normalized
    base = normalized.split("-", 1)[0]
    if base in TRANSLATION_OVERRIDES or base == DEFAULT_LANGUAGE:
        return base
    return None


def resolve_language(stored: Any, accept_language: str = "") -> str:
    selected = supported_language(stored)
    if selected:
        return selected

    preferences: list[tuple[float, int, str]] = []
    for position, item in enumerate(accept_language.split(",")):
        parts = [part.strip() for part in item.split(";")]
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.lower().startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        if quality > 0:
            preferences.append((quality, position, parts[0]))

    for _, _, language_range in sorted(
        preferences,
        key=lambda item: (-item[0], item[1]),
    ):
        selected = supported_language(language_range)
        if selected:
            return selected
    return DEFAULT_LANGUAGE


def translations_for(language: str) -> dict[str, str]:
    return {**ENGLISH, **TRANSLATION_OVERRIDES.get(language, {})}


def direction_for(language: str) -> str:
    return "rtl" if language == "ar" else "ltr"


def translate_portal_error(message: str, translations: dict[str, str]) -> str:
    key = ERROR_TRANSLATION_KEYS.get(message)
    return translations.get(key, message) if key else message
