def fetch_data_from_api(raspberry_pi_id=None, seconds=None):
    base_url = reverse('sensor-data')
    logger.debug(f"Fetching data from {base_url}...")  # Agrega este log
    params = {}
    if seconds:
        params["seconds"] = seconds
    else:
        params["seconds"] = LATEST_DATA_MINUTES * 60

    if raspberry_pi_id:
        base_url += f"{raspberry_pi_id}/"

    response = requests.get(base_url, params=params)
    logger.debug(f"Response status: {response.status_code}")
    logger.debug(f"Response data: {response.json()}")
    return response.json()

def latest_data_table(request):
    try:
        data = fetch_data_from_api()
        logger.debug(f"Data for table: {data}")
        return render(request, 'partials/latest-data-table-rows.html', {'data': data})
    except Exception as e:
        logger.error(f"Error rendering latest data table: {str(e)}")
        return JsonResponse(
            {"error": "Error rendering latest data table", "detail": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def latest_data_chart(request):
    logger.debug("Fetching data for chart...")
    data = fetch_data_from_api()

    if data:
        df = pd.DataFrame(data)
        data_json = df.to_json(orient='records', date_format='iso')
    else:
        data_json = "[]"

    context = {
        'data_json': data_json
    }
    return render(request, 'partials/latest-data-chart.html', context)