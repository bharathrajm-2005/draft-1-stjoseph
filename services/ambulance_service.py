from database.models import db, Ambulance
from utils.logger import app_logger
import math
import random
from datetime import datetime

class AmbulanceService:
    def __init__(self):
        # Simulated hospital location (Bangalore central)
        self.hospital_lat = 12.9716
        self.hospital_lng = 77.5946

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # convert decimal degrees to radians 
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers. Use 3956 for miles
        return c * r

    def find_nearest_drivers(self, target_lat=None, target_lng=None, count=2):
        """
        Finds the nearest Available drivers using Haversine distance.
        Returns a list of Ambulance objects.
        """
        lat = target_lat if target_lat is not None else self.hospital_lat
        lng = target_lng if target_lng is not None else self.hospital_lng
        
        # Only Available drivers receive alerts
        available = Ambulance.query.filter_by(status='Available').all()
        if not available:
            return []
            
        def dist_haversine(amb):
            return self.haversine_distance(amb.current_lat, amb.current_lng, lat, lng)
            
        sorted_ambs = sorted(available, key=dist_haversine)
        return sorted_ambs[:count]

    def simulate_realtime_movement(self):
        """
        Subtly jitters available ambulances and moves busy ones towards target.
        """
        ambulances = Ambulance.query.all()
        for amb in ambulances:
            if amb.status == "Available":
                # Regular jitter
                amb.current_lat += (random.random() - 0.5) * 0.0001
                amb.current_lng += (random.random() - 0.5) * 0.0001
            elif amb.status == "Busy" and amb.target_lat and amb.target_lng:
                # Move towards target
                step = 0.0005
                d_lat = amb.target_lat - amb.current_lat
                d_lng = amb.target_lng - amb.current_lng
                
                dist = math.sqrt(d_lat**2 + d_lng**2)
                if dist < step:
                    amb.current_lat = amb.target_lat
                    amb.current_lng = amb.target_lng
                    # amb.status = "On Duty" # Not specified in 1B, keeping it Busy
                else:
                    amb.current_lat += (d_lat / dist) * step
                    amb.current_lng += (d_lng / dist) * step
            
            amb.last_update = datetime.utcnow()
        
        db.session.commit()

    def check_and_escalate_dispatches(self):
        """
        Background check: Escalates Pending requests/dispatches to secondary driver after 3 minutes.
        Called by heartbeat/polling.
        """
        from database.models import EmergencyDispatch, EmergencyRequest
        from datetime import timedelta
        
        threshold = datetime.utcnow() - timedelta(minutes=3)
        
        # Original Dispatches
        pending_dispatches = EmergencyDispatch.query.filter_by(dispatch_status='Pending').all()
        for d in pending_dispatches:
            if d.first_alert_time < threshold:
                d.dispatch_status = 'Escalated'
                d.second_alert_time = datetime.utcnow()
        
        # New Emergency Requests
        pending_requests = EmergencyRequest.query.filter_by(status='Pending').all()
        for r in pending_requests:
            if r.created_at < threshold:
                r.status = 'Escalated'
                app_logger.info(f"🚨 SOS ESCALATED: Request #{r.id} for {r.patient_name} shifted to Secondary Driver.")
        
        db.session.commit()

    def dispatch_ambulance(self, appointment, patient_lat=None, patient_lng=None):
        """
        Step 1 & 2: Nearest driver selection and EmergencyDispatch creation.
        """
        if appointment.appointment_type != "Emergency":
            return None
            
        p_lat = patient_lat if patient_lat else self.hospital_lat + (random.random() - 0.5) * 0.1
        p_lng = patient_lng if patient_lng else self.hospital_lng + (random.random() - 0.5) * 0.1
        
        nearest_ambs = self.find_nearest_drivers(p_lat, p_lng, count=2)
        if not nearest_ambs:
            app_logger.warning("No available ambulances for emergency dispatch!")
            return None
            
        primary = nearest_ambs[0]
        # Fallback to primary if only 1 available
        secondary = nearest_ambs[1] if len(nearest_ambs) > 1 else nearest_ambs[0]
        
        from database.models import EmergencyDispatch
        dispatch = EmergencyDispatch(
            appointment_id=appointment.id,
            primary_driver_id=primary.driver_id,
            secondary_driver_id=secondary.driver_id,
            dispatch_status="Pending",
            first_alert_time=datetime.utcnow()
        )
        
        # We'll store target on the ambulance only AFTER acceptance in Phase 1B
        # But we need to know where the patient is. Let's add target to dispatch.
        db.session.add(dispatch)
        db.session.commit()
        
        app_logger.info(f"🚨 FORCED DISPATCH: Primary {primary.driver_name}, Secondary {secondary.driver_name} for Appt #{appointment.id}")
        return primary

    def handle_emergency_request(self, name, phone, address, lat=None, lng=None):
        """AI DRIVER SELECTION LOGIC: Assigns the nearest single available driver from the fleet of 5."""
        from database.models import EmergencyRequest, Ambulance
        from utils.logger import app_logger

        # 1. Store record
        req = EmergencyRequest(
            patient_name=name,
            phone_number=phone,
            address=address,
            latitude=lat,
            longitude=lng,
            status='Dispatched' # Direct to dispatched as it's an SOS
        )
        db.session.add(req)
        db.session.flush()

        # 2. Find nearest available driver (Strict check for status='Available')
        amb = None
        if lat and lng:
            # Haversine nearest
            nearest = self.find_nearest_drivers(lat, lng, count=1)
            amb = nearest[0] if nearest else None
        else:
            # First available (fallback if GPS fails)
            amb = Ambulance.query.filter_by(status='Available').first()

        if not amb:
            db.session.rollback()
            app_logger.error(f"❌ SOS DISPATCH FAILED: No available ambulances for {name} ({phone})")
            return None
            
        # 3. Assign and Lock - AI AUTOMATION
        req.assigned_driver_id = amb.driver_id
        
        # Lock ambulance immediately
        amb.status = "Busy"
        if lat and lng:
            amb.target_lat = lat
            amb.target_lng = lng
        
        db.session.commit()
        app_logger.info(f"🚑 AI AUTO-DISPATCH: SOS #{req.id} assigned to driver {amb.driver_name} for patient {name}")
        return req

    def get_all_ambulances(self):
        # Simulate movement and check escalations
        try:
            self.simulate_realtime_movement()
            self.check_and_escalate_dispatches()
        except Exception as e:
            app_logger.error(f"Heartbeat error: {str(e)}")
        return Ambulance.query.all()
