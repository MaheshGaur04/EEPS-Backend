"""API smoke tests against a running server on localhost:5000."""
import json
import urllib.error
import urllib.request
import http.cookiejar

BASE = 'http://127.0.0.1:5000/api'
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def req(method, path, data=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = None if data is None else json.dumps(data).encode('utf-8')
    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with opener.open(request, timeout=20) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8')
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {'raw': raw}
        return e.code, payload


def main():
    results = []

    code, data = req('GET', '/health')
    results.append(('health', code, data.get('status') or data))

    code, data = req('POST', '/auth/login', {
        'identifier': 'admin@earthenergy.local',
        'password': 'Admin@12345',
    })
    results.append(('admin_login', code, data.get('user', {}).get('role') if code == 200 else data))
    admin_token = data.get('accessToken') if code == 200 else None

    code, data = req('POST', '/auth/register', {
        'fullName': 'Test Customer',
        'email': 'customer.smoke@example.com',
        'mobile': '9887766554',
        'password': 'Test@12345Strong!',
        'location': 'Hamirpur, Uttar Pradesh',
        'role': 'CUSTOMER',
    })
    results.append(('register', code, data.get('message') if code in (200, 201) else data))

    code, data = req('POST', '/auth/login', {
        'identifier': 'customer.smoke@example.com',
        'password': 'Test@12345Strong!',
    })
    results.append(('customer_login', code, data.get('user', {}).get('role') if code == 200 else data))
    cust_token = data.get('accessToken') if code == 200 else None

    if cust_token:
        code, data = req('GET', '/auth/me', token=cust_token)
        results.append(('me', code, data.get('user', {}).get('email') if code == 200 else data))

        code, data = req('POST', '/service-requests/', {
            'subject': 'Roof inspection',
            'category': 'Maintenance',
            'serviceType': 'Inspection',
            'systemSize': '5 kW',
            'propertyAddress': 'Near UP Gramin Bank, Hamirpur UP 210431',
            'priority': 'HIGH',
            'description': 'Please inspect my rooftop solar mounting structure.',
        }, token=cust_token)
        results.append(('create_sr', code, data.get('message') if code in (200, 201) else data))

        code, data = req('GET', '/service-requests/', token=cust_token)
        results.append(('list_sr', code, len(data.get('serviceRequests', [])) if code == 200 else data))

        code, data = req('POST', '/roi/calculate', {
            'monthlyBill': 6000,
            'averageLoadKw': 4,
            'rooftopSizeSqft': 450,
            'location': 'Hamirpur, Uttar Pradesh',
            'roofType': 'Sloped',
            'batteryBackup': False,
        }, token=cust_token)
        results.append(('roi', code, data.get('estimate', {}).get('source') if code == 200 else data))

    code, data = req('POST', '/contact/', {
        'name': 'Smoke Tester',
        'email': 'smoke@example.com',
        'phone': '9876543210',
        'message': 'Interested in a free site survey for rooftop solar.',
        'source': 'smoke_test',
    })
    results.append(('contact', code, data.get('message') if code in (200, 201) else data))

    if admin_token:
        code, data = req('GET', '/admin/users', token=admin_token)
        results.append(('admin_users', code, len(data.get('users', [])) if code == 200 else data))
        code, data = req('GET', '/admin/contacts', token=admin_token)
        results.append(('admin_contacts', code, len(data.get('contacts', [])) if code == 200 else data))
        code, data = req('GET', '/admin/service-requests', token=admin_token)
        results.append(('admin_srs', code, data.get('total') if code == 200 else data))

    print('=== SMOKE TEST RESULTS ===')
    failed = 0
    for name, code, detail in results:
        ok = 200 <= int(code) < 300
        if not ok:
            failed += 1
        print(f"{'PASS' if ok else 'FAIL'} {name}: HTTP {code} -> {detail}")
    print(f'Total: {len(results)}, Failed: {failed}')
    return failed


if __name__ == '__main__':
    raise SystemExit(main())
