rm(list=ls())
#install.packages("GeoModels",dependencies=TRUE)
library(GeoModels)
library(fields)

model="Beta2"
copula="Clayton"


set.seed(22601)


#########
# Define the spatial-coordinates of the points:
NN=800
x <- runif(NN);y <- runif(NN)
coords=cbind(x,y)
#########

## regression matrix
X=cbind(rep(1,NN),runif(NN))


###############################
##setting parameteters
###############################
## marginal parameters
mean=0.2       # beta0 regression parameter
mean1=-0.2     #beta1 regression parameter
shape=2      # shape parametere


## underlying correlation parameters
corrmodel="GenWend" 
scale=0.15;power2=4;smooth=0;sill=1;nugget=0

### Clayton copula asymmetry parameter
nu=1

### bounded of the beta RF
min=0;max=1
###############################
###############################


#######################################################################################
#######################################################################################
############ Simulation of the Beta RF using the clayton copula #######################
#######################################################################################
#######################################################################################
param=list(smooth=smooth,power2=power2, min=min,max=max,
           mean=mean,mean1=mean1,
           nu=nu,
           sill=sill,scale=scale,nugget=nugget,shape=shape)

data <- GeoSimCopula(coordx=coords, corrmodel=corrmodel, model=model,param=param,X=X,
                     copula=copula)$data
#######################################################################################
#######################################################################################





##############################################################
### analysis assuming independence 
##############################################################
optimizer="nlminb"
I=5
fixed<-list(nugget=nugget,sill=sill,scale=scale,smooth=smooth,power2=power2,min=min,max=max,nu=nu)
start<-list(shape=shape,mean=mean,mean1=mean1)
lower<-list(shape=0,mean=-I,mean1=-I)
upper<-list(shape=1000,mean=I,mean1=I)

#### maximum independence likelihood
fit0 <- GeoFit(data=data,coordx=coords,corrmodel=corrmodel, model=model,likelihood="Marginal",type="Independence",
                      optimizer=optimizer,lower=lower,upper=upper,copula=copula,X=X,
                      start=start,fixed=fixed)

## a qq plot 
GeoQQ(fit0)

## normal score transformation
bb=GeoPit(fit0,type="Gaussian")
hist(bb$data,freq=FALSE)

# type of bivariate dependence
GeoScatterplot(bb$data,coords,neighb=c(1,2,3,4))
##############################################################
##############################################################





#################################################################################################################
#################################################################################################################
##################### Estimation ################################################################################
#################################################################################################################
#################################################################################################################





#################################################################################################################
############### Clayton copula model ############################################################################
############### estimating marginal and dependence parameters with ##############################################
############### weigthed composite likelihood                     ###############################################
#################################################################################################################

optimizer="nlminb"
I=50
start1<-list(shape=shape,mean=mean,mean1=mean1,scale=scale)
lower<-list(shape=0,mean=-I,mean1=-I,scale=0)
upper<-list(shape=I,mean=I,mean1=I,scale=2)

fixed1<-list(sill=sill,smooth=smooth,power2=power2,min=min,max=max,nugget=nugget,nu=nu)

fit1<- GeoFit(data=data,coordx=coords,corrmodel=corrmodel, model=model,X=X,
               neighb=2,likelihood="Marginal",type="Pairwise",sensitivity=TRUE,
               optimizer=optimizer,lower=lower,upper=upper,
               copula="Clayton",
               start=start1,fixed=fixed1)


################################
### estimating std err and PLIC
################################
a=GeoVarestbootstrap(fit1,K=250,optimizer="nlminb",lower=lower,upper=upper)






#################################################################################################################
############### Gaussian copula model ###########################################################################
############### estimating marginal and dependence parameters with ##############################################
############### weigthed composite likelihood                     ###############################################
#################################################################################################################


optimizer="nlminb"
I=50
start1<-list(shape=shape,mean=mean,mean1=mean1,scale=scale)
lower<-list(shape=0,mean=-I,mean1=-I,scale=0)
upper<-list(shape=I,mean=I,mean1=I,scale=2)

fixed1<-list(sill=sill,smooth=smooth,power2=power2,min=min,max=max,nugget=nugget)

fit2<- GeoFit(data=data,coordx=coords,corrmodel=corrmodel, model=model,X=X,
               neighb=2,likelihood="Marginal",type="Pairwise",sensitivity=TRUE,
               optimizer=optimizer,lower=lower,upper=upper,
               copula="Gaussian",
               start=start1,fixed=fixed1)

################################
### estimating std err and PLIC
################################
b=GeoVarestbootstrap(fit2,K=250,optimizer="nlminb",lower=lower,upper=upper)





