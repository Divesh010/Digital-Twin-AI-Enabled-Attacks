import re
path = r'C:\Users\Dell\Documents\SmartCampusDigitalTwin\tests\test_transport.py'
with open(path, 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace(
    '# 24192 expected for 7 days, 12 rooms, 5min dt\n    assert len(df) == 24192',
    '# dynamically calculate expected rows\n    expected_rows = int((config.simulation.end_datetime - config.simulation.start_datetime).total_seconds() / config.simulation.dt_seconds) * len(sim.rooms)\n    assert len(df) == expected_rows'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(t)
print('Fixed test_transport.py')
