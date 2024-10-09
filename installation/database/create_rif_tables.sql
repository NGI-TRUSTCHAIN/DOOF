CREATE TABLE IF NOT EXISTS rif_advertisement(
            id UUID DEFAULT uuid_generate_v1() PRIMARY KEY,
            ads_lock TEXT NOT NULL,
            description TEXT NOT NULL,   
            purpose_id UUID NOT NULL,
            partner_id UUID NOT NULL,
            recipient_ads_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), 
            CONSTRAINT purpose_id_fkey FOREIGN KEY (purpose_id) 
                REFERENCES purpose_of_usage(id) MATCH SIMPLE
                ON UPDATE NO ACTION ON DELETE NO ACTION,

            CONSTRAINT partner_id_fkey FOREIGN KEY(partner_id)
                REFERENCES account(id) MATCH SIMPLE 
                ON UPDATE NO ACTION ON DELETE NO ACTION
         );

CREATE TABLE IF NOT EXISTS rif_advertisement_interest(
            id UUID DEFAULT uuid_generate_v1() PRIMARY KEY,
            account_id UUID,
            advertisement_id UUID,
            accept BOOLEAN,
            product_id UUID, 
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), 
            CONSTRAINT adv_id_fkey FOREIGN KEY (advertisement_id) 
                REFERENCES rif_advertisement(id) 
                ON UPDATE NO ACTION ON DELETE NO ACTION, 

            CONSTRAINT product_id_fkey FOREIGN KEY (product_id)
                REFERENCES product (id) MATCH SIMPLE
                ON UPDATE NO ACTION ON DELETE NO ACTION,
            
            CONSTRAINT account_id_fkey FOREIGN KEY(account_id)
                REFERENCES account(id) MATCH SIMPLE 
                ON UPDATE NO ACTION ON DELETE NO ACTION,
            
            unique(advertisement_id, product_id)
        );

CREATE TABLE IF NOT EXISTS rif_private_message (
            id UUID DEFAULT uuid_generate_v1() PRIMARY KEY,
            lock TEXT NOT NULL,
            subscription_id UUID,
            message TEXT,
            send_to UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT account_to_fkey FOREIGN KEY(send_to)
                REFERENCES account(id) MATCH SIMPLE 
                ON UPDATE NO ACTION ON DELETE NO ACTION
        );

CREATE TABLE IF NOT EXISTS rif_subscription_news (
            id UUID DEFAULT uuid_generate_v1() PRIMARY KEY,
            subscription_id UUID NOT NULL,
            product_id UUID NOT NULL, 
            supplicant_id UUID NOT NULL, 
            purpose_id UUID NOT NULL,
            action int NOT NULL,
            send_to UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT product_id_fkey FOREIGN KEY (product_id)
                REFERENCES product (id) MATCH SIMPLE
                ON UPDATE NO ACTION ON DELETE NO ACTION,
            CONSTRAINT supplicant_fkey FOREIGN KEY(supplicant_id)
                REFERENCES account(id) MATCH SIMPLE 
                ON UPDATE NO ACTION ON DELETE NO ACTION,
            CONSTRAINT purpose_id_fkey FOREIGN KEY (purpose_id) 
                REFERENCES purpose_of_usage(id) MATCH SIMPLE
                ON UPDATE NO ACTION ON DELETE NO ACTION,
            CONSTRAINT account_to_fkey FOREIGN KEY(send_to)
                REFERENCES account(id) MATCH SIMPLE 
                ON UPDATE CASCADE ON DELETE CASCADE
        );


