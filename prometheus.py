from aioprometheus import Counter

bot_requests_cnt = Counter("admission_bot_requests", "Bot requests counter")
user_registrations_cnt = Counter("admission_bot_user_registrations", "Bot user registrations counter")
user_full_registrations_cnt = Counter("admission_bot_user_full_registrations", "Bot user full registrations counter")
get_my_queue_cnt = Counter("admission_bot_get_my_queue", "Bot GetMyQueue calls counter")
queue_registrations_cnt = Counter("admission_bot_queue_regisrations", "Bot RegInQueue calls counter")
geo_sent_cnt = Counter("admission_bot_geo_sent", "Bot Geo sent times counter")
help_btn_cnt = Counter("admission_bot_help_btn", "Bot Help button clicks counter")
start_handler_cnt = Counter("admission_bot_start_handler", "Start handler called times counter")
api_requests_cnt = Counter("admission_bot_api_requests", "Bot to Admission API requests counter")
