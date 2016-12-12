
#Update CREA Stats
UPDATE h_stats set avg_house = (select avg(lp_dol) from h_housetmp where s_r='Sale' and lp_dol > 1000) where date=CURRENT_DATE( );
UPDATE h_stats set t_house = (select count(*) from h_housetmp ) where date=CURRENT_DATE( );



#Generate Data for CITY CHART
delete from h_stats_chart where chartname='city';
#INSERT h_stats_chart (chartname,n1,n3,i1,i2,n4,n2)
#SELECT 'city', m.municipality_cname as cname, h.municipality as ename,
#count(*) as count,round(avg(lp_dol/10000)) as price_avg,
#h.county province, c.name as provincec
#FROM h_housetmp h,h_mname m,h_city c
#WHERE h.municipality = m.municipality
#AND h.county = c.englishname
#GROUP BY h.municipality  HAVING count > 50
#order by count desc;

INSERT h_stats_chart (chartname,n1,n3,i1,i2,n4,n2)
SELECT 'city', m.municipality_cname as cname, h.municipality as ename,
count(*) as count,round(avg(lp_dol/10000)) as price_avg,
h.county as province, c.name as provincec
FROM h_housetmp h,h_mname m,h_city c
WHERE h.municipality = m.municipality
AND h.county = c.englishname
GROUP BY h.municipality,h.county,c.name   HAVING count > 50
order by count desc;


#Generate Data for Province CHART
delete from h_stats_chart where chartname='province';
INSERT h_stats_chart (chartname,i1,i2,n4,n2)
SELECT 'province', count(*) as count,round(avg(lp_dol/10000)) as price_avg,
h.county province, c.name as provincec
FROM h_housetmp h,h_city c
WHERE h.county = c.englishname
AND h.county !='' 
GROUP BY h.county, c.name 
order by count desc;


#Generate Data for Type Chart
delete from h_stats_chart where chartname='type';
INSERT h_stats_chart (chartname,i1,n1,i2)
SELECT 'type',count(*) as count,p.name as cname, round(avg(lp_dol/10000))
FROM h_housetmp h,h_property_type p 
WHERE h.propertytype_id = p.id group by h.propertytype_id ;


#Generate Data for Price Chart
delete from h_stats_chart where chartname='price';
INSERT h_stats_chart (chartname,n1,i1)
SELECT 'price',floor(lp_dol/200000)*20 as bin, count(*) as count
from h_housetmp 
where lp_dol > 100 and s_r ='Sale' and lp_dol < 4000000
group by bin ;


#Generate Data for House Area Chart
delete from h_stats_chart where chartname='house';
INSERT h_stats_chart (chartname,n1,i1)
SELECT 'house',floor(house_area/500)*500 as bin, count(*) as count
from h_housetmp 
where house_area > 100 and house_area < 6000 
group by bin ;



#Generate Data for Land Area Chart
delete from h_stats_chart where chartname='land';
INSERT h_stats_chart (chartname,n1,i1)
SELECT 'land',floor(land_area/1000)*1000 as bin, count(*) as count
from h_housetmp 
where land_area > 100 and land_area < 20000 
group by bin ;

#Update IDX house SRC flag
update h_housetmp,idx_mls set h_housetmp.src="IDX" where h_housetmp.ml_num = idx_mls.ml_num;
